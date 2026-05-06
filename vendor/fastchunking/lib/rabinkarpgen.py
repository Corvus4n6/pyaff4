import pybindgen

def generate(file_):
    mod = pybindgen.Module('rabinkarprh')
    mod.add_include('"rabinkarp.h"')
    mod.add_container('std::list<int>', 'int', 'list')
    mod.add_container('std::list<double>', 'double', 'list')

    klass = mod.add_class('RabinKarpHash')
    klass.add_constructor([pybindgen.param('int', 'my_window_size'),
                           pybindgen.param('int', 'seed')])
    klass.add_method('set_threshold',
                     None,
                     [pybindgen.param('double', 'my_threshold')])
    klass.add_method('set_thresholds',
                     None,
                     [pybindgen.param('std::list<double>', 'my_thresholds')])
    klass.add_method('get_all_chunk_boundaries',
                     pybindgen.retval('std::list<int>'),
                     [pybindgen.param('std::string*', 'str'),
                      pybindgen.param('unsigned int', 'prepend_bytes')])
    klass.add_method('get_all_chunk_boundaries_with_thresholds',
                     pybindgen.retval('std::list<int>'),
                     [pybindgen.param('std::string*', 'str'),
                      pybindgen.param('unsigned int', 'prepend_bytes')])
    
    mod.generate(file_)
