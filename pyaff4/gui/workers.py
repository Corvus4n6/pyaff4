import os
import time
from PySide6.QtCore import QThread, Signal, QObject

from pyaff4 import container, rdfvalue, data_store, lexicon, linear_hasher, hashes, aff4, block_hasher, logical


class _Progress:
    """Adapter from pyaff4 progress callback to a Qt signal."""
    def __init__(self, signal, total):
        self._signal = signal
        self._total = total
        self._last_report = 0

    def Report(self, done):
        if self._total > 0:
            pct = min(100, int(done * 100 / self._total))
            if pct != self._last_report:
                self._last_report = pct
                self._signal.emit(pct)


class VerifyWorker(QThread):
    """Verify all images in an AFF4 container."""
    progress = Signal(int)            # 0-100 per image
    image_started = Signal(str)       # image display name
    hash_result = Signal(str, str, str, str, bool)  # image_name, algo, stored, calculated, valid
    status = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            urn = rdfvalue.URN.FromFileName(self.file_path)
            with container.Container.openURNtoContainer(urn) as volume:
                if isinstance(volume, container.PhysicalImageContainer):
                    self._verify_physical(volume)
                elif isinstance(volume, container.LogicalImageContainer):
                    self._verify_logical(volume)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _verify_logical(self, volume):
        images = list(volume.images())
        for i, image in enumerate(images):
            if self._cancelled:
                break
            name = str(image.name())
            self.image_started.emit(name)
            self.status.emit("Hashing %s..." % name)
            self.progress.emit(0)

            storedHashes = list(volume.resolver.QuerySubjectPredicate(
                image.container.urn, image.urn, lexicon.standard.hash))

            worker_self = self

            class Listener:
                def onValidHash(self, typ, hash_val, urn):
                    worker_self.hash_result.emit(name, typ, hash_val, hash_val, True)
                def onInvalidHash(self, typ, stored, calculated, urn):
                    worker_self.hash_result.emit(name, typ, stored, calculated, False)

            hasher = linear_hasher.LinearHasher2(volume.resolver, Listener())

            try:
                with volume.resolver.AFF4FactoryOpen(image.urn, version=image.container.version) as stream:
                    size = stream.Size()
                prog = _Progress(self.progress, size)
                hasher.hash(image, progress=prog)
            except Exception as e:
                self.error.emit("Error hashing %s: %s" % (name, str(e)))

    def _verify_physical(self, volume):
        self.status.emit("Verifying physical image...")
        self.progress.emit(0)

        worker_self = self
        block_failures = [0]

        class Listener:
            def onValidBlockHash(self, a): pass
            def onInvalidBlockHash(self, a, b, imageStreamURI, offset):
                block_failures[0] += 1
            def onValidHash(self, typ, hash_val, urn):
                worker_self.hash_result.emit(str(urn), str(typ), str(hash_val), str(hash_val), True)
            def onInvalidHash(self, typ, a, b, urn):
                worker_self.hash_result.emit(str(urn), str(typ), str(a), str(b), False)

        validator = block_hasher.Validator(Listener())
        validator.validateContainer(rdfvalue.URN.FromFileName(self.file_path))

        # Summarise block-level hash results as a single row
        container_str = str(rdfvalue.URN.FromFileName(self.file_path))
        if block_failures[0] == 0:
            self.hash_result.emit(container_str, "BlockHashes", "PASS", "PASS", True)
        else:
            fail_msg = "%d block(s) failed" % block_failures[0]
            self.hash_result.emit(container_str, "BlockHashes", fail_msg, fail_msg, False)


class AddImagesWorker(QThread):
    """Add files/folders to an existing AFF4 container."""
    progress = Signal(int)     # 0-100 overall
    status = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, container_path, source_paths):
        super().__init__()
        self.container_path = container_path
        self.source_paths = source_paths  # list of file paths
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _collect_files(self):
        """Expand any directories into individual files."""
        result = []
        for path in self.source_paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for fname in files:
                        result.append(os.path.join(root, fname))
            else:
                result.append(path)
        return result

    def run(self):
        try:
            files = self._collect_files()
            total = len(files)
            urn = rdfvalue.URN.FromFileName(self.container_path)
            with container.Container.openURNtoContainer(urn, mode="+") as volume:
                for i, fpath in enumerate(files):
                    if self._cancelled:
                        break
                    fname = os.path.basename(fpath)
                    self.status.emit("Adding %s..." % fname)
                    size = os.path.getsize(fpath)
                    fsmeta = logical.FSMetadata.create(fpath)
                    with open(fpath, "rb") as f:
                        hasher = linear_hasher.StreamHasher(f, [lexicon.HASH_SHA1, lexicon.HASH_MD5])
                        urn = volume.writeLogicalStream(fpath, hasher, size)
                        for h in hasher.hashes:
                            hh = hashes.newImmutableHash(h.hexdigest(), hasher.hashToType[h])
                            volume.resolver.Add(urn, urn, rdfvalue.URN(lexicon.standard.hash), hh)
                    fsmeta.urn = urn
                    fsmeta.store(volume.resolver)
                    self.progress.emit(int((i + 1) * 100 / total))
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class CreateVolumeWorker(QThread):
    """Create a new AFF4 logical image container and optionally add files."""
    progress = Signal(int)
    status = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, output_path, case_name, examiner, description, source_paths,
                 path_mode="Store full paths"):
        super().__init__()
        self.output_path = output_path
        self.case_name = case_name
        self.examiner = examiner
        self.description = description
        self.source_paths = source_paths
        self.path_mode = path_mode
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _collect_files(self):
        """Return (absolute_path, source_root) pairs."""
        result = []
        for path in self.source_paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for fname in files:
                        result.append((os.path.join(root, fname), path))
            else:
                result.append((path, path))
        return result

    def _stored_path(self, fpath, source_root):
        """Return the path string to store in the container based on path_mode."""
        if self.path_mode == "Strip paths":
            return os.path.basename(fpath)
        elif self.path_mode == "Store relative paths":
            norm = os.path.normpath(source_root)
            if os.path.isdir(norm):
                # relative to the parent of the selected folder,
                # so the folder name itself is preserved in the stored path
                return os.path.relpath(fpath, os.path.dirname(norm))
            else:
                return os.path.basename(fpath)
        else:  # "Store full paths"
            return fpath

    def run(self):
        try:
            resolver = data_store.MemoryDataStore()
            container_urn = rdfvalue.URN.FromFileName(self.output_path)
            resolver.Set(lexicon.transient_graph, container_urn,
                         lexicon.AFF4_STREAM_WRITE_MODE, rdfvalue.XSDString("truncate"))

            self.status.emit("Creating container...")
            with container.Container.createURN(resolver, container_urn, zip_based=True) as volume:
                # Write case metadata
                if self.case_name or self.examiner or self.description:
                    self._write_case_metadata(resolver, volume)

                files = self._collect_files()
                total = len(files)
                for i, (fpath, source_root) in enumerate(files):
                    if self._cancelled:
                        break
                    fname = os.path.basename(fpath)
                    self.status.emit("Adding %s..." % fname)
                    size = os.path.getsize(fpath)
                    stored_path = self._stored_path(fpath, source_root)
                    fsmeta = logical.FSMetadata.create(fpath)
                    with open(fpath, "rb") as f:
                        hasher = linear_hasher.StreamHasher(f, [lexicon.HASH_SHA1, lexicon.HASH_MD5])
                        urn = volume.writeLogicalStream(stored_path, hasher, size)
                        for h in hasher.hashes:
                            hh = hashes.newImmutableHash(h.hexdigest(), hasher.hashToType[h])
                            resolver.Add(urn, urn, rdfvalue.URN(lexicon.standard.hash), hh)
                    fsmeta.urn = urn
                    fsmeta.store(resolver)
                    pct = int((i + 1) * 100 / max(total, 1))
                    self.progress.emit(pct)

            self.status.emit("Done.")
            self.progress.emit(100)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _write_case_metadata(self, resolver, volume):
        case_urn = volume.urn.Append("CaseDetails")
        resolver.Add(volume.urn, case_urn,
                     rdfvalue.URN(lexicon.AFF4_TYPE),
                     rdfvalue.URN(volume.lexicon.of("CaseDetails")))
        if self.case_name:
            resolver.Set(volume.urn, case_urn,
                         rdfvalue.URN(volume.lexicon.of("caseName")),
                         rdfvalue.XSDString(self.case_name))
        if self.examiner:
            resolver.Set(volume.urn, case_urn,
                         rdfvalue.URN(volume.lexicon.of("examiner")),
                         rdfvalue.XSDString(self.examiner))
        if self.description:
            resolver.Set(volume.urn, case_urn,
                         rdfvalue.URN(volume.lexicon.of("caseDescription")),
                         rdfvalue.XSDString(self.description))
