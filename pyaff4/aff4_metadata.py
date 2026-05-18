class RDFObject:
    def __init__(self, URN, resolver, lexicon):
        self.resolver = resolver
        self.urn = URN
        self.lexicon = lexicon

    def __getattr__(self, item):
        val = self.resolver.GetUnique(None, self.urn, self.lexicon.of(item))
        return val