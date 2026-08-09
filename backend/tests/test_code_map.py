import sys
import os
import tempfile
import unittest

# Ensure the backend directory is in the path to import agents.code_map
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.code_map import CodeMapper, get_code_mapper, SymbolLocation

class TestCodeMap(unittest.TestCase):
    def setUp(self):
        self.mapper = CodeMapper()
        
    def test_parse_python_symbols(self):
        content = '''
import os
from sys import path

class ServiceManager:
    def initialize(self, config: dict) -> bool:
        pass

async def async_func(a, b):
    return a + b
'''
        symbols = self.mapper.parse_python_symbols('test.py', content)
        self.assertEqual(len(symbols), 5)
        self.assertEqual(symbols[0].name, 'os')
        self.assertEqual(symbols[0].symbol_type, 'import')
        self.assertEqual(symbols[1].name, 'path')
        self.assertEqual(symbols[2].name, 'ServiceManager')
        self.assertEqual(symbols[2].symbol_type, 'class')
        self.assertEqual(symbols[3].name, 'initialize')
        self.assertEqual(symbols[3].symbol_type, 'method')
        self.assertEqual(symbols[4].name, 'async_func')
        self.assertEqual(symbols[4].symbol_type, 'function')
        
    def test_parse_js_ts_symbols(self):
        content = '''
import React from 'react';
export class Header extends Component {
}
function helper() {}
export const MY_CONST = () => {}
'''
        symbols = self.mapper.parse_js_ts_symbols('test.ts', content)
        self.assertEqual(len(symbols), 4)
        self.assertEqual(symbols[0].symbol_type, 'import')
        self.assertEqual(symbols[1].name, 'Header')
        self.assertEqual(symbols[1].symbol_type, 'export')
        self.assertEqual(symbols[2].name, 'helper')
        self.assertEqual(symbols[2].symbol_type, 'function')
        self.assertEqual(symbols[3].name, 'MY_CONST')
        self.assertEqual(symbols[3].symbol_type, 'export')

    def test_build_repo_map(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mapper = CodeMapper(tmpdir)
            with open(os.path.join(tmpdir, 'test.py'), 'w', encoding='utf-8') as f:
                f.write('class A:\n  pass')
            
            repo_map = mapper.build_repo_map()
            self.assertIn('test.py:', repo_map)
            self.assertIn('class A', repo_map)
            
    def test_find_definition_and_references(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mapper = CodeMapper(tmpdir)
            with open(os.path.join(tmpdir, 'def.py'), 'w', encoding='utf-8') as f:
                f.write('def my_unique_func():\n  pass\n')
            with open(os.path.join(tmpdir, 'ref.py'), 'w', encoding='utf-8') as f:
                f.write('my_unique_func()\n')
                
            defs = mapper.find_definition('my_unique_func')
            self.assertEqual(len(defs), 1)
            self.assertEqual(defs[0].symbol_type, 'function')
            
            refs = mapper.find_references('my_unique_func')
            self.assertTrue(len(refs) >= 1)
            self.assertEqual(refs[0].symbol_type, 'reference')
            
    def test_singleton(self):
        mapper1 = get_code_mapper('/workspace1')
        mapper2 = get_code_mapper('/workspace1')
        self.assertIs(mapper1, mapper2)
        
        mapper3 = get_code_mapper('/workspace2')
        self.assertIsNot(mapper1, mapper3)
        self.assertEqual(mapper3.workspace_dir, '/workspace2')

if __name__ == '__main__':
    unittest.main()
