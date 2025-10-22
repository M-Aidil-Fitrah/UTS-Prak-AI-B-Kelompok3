"""Test Runner - Menjalankan semua test suite.

Script ini menjalankan semua test:
- test_core.py: Test modul core (inference_engine, search_filter, models)
- test_services.py: Test modul services (logging, storage, reporting)
- test_integration.py: Test integrasi antar modul

Usage:
    python app/tests/run_tests.py
    python app/tests/run_tests.py --verbose
    python app/tests/run_tests.py --suite core
    python app/tests/run_tests.py --suite services
    python app/tests/run_tests.py --suite integration
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Tambahkan app/ ke path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

# Import test modules
from tests import test_core, test_services, test_integration


class TestRunner:
    """Orchestrates running all test suites."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = {
            'core': {'total': 0, 'passed': 0, 'failed': 0, 'errors': []},
            'services': {'total': 0, 'passed': 0, 'failed': 0, 'errors': []},
            'integration': {'total': 0, 'passed': 0, 'failed': 0, 'errors': []},
        }
    
    def run_suite(self, suite_name, test_module):
        """Run a single test suite."""
        print(f"\n{'='*60}")
        print(f"Running {suite_name.upper()} Tests")
        print(f"{'='*60}")
        
        # Capture original stdout if not verbose
        import io
        if not self.verbose:
            original_stdout = sys.stdout
            sys.stdout = io.StringIO()
        
        try:
            # Run the test module
            success = test_module.run_all_tests()
            
            # Restore stdout
            if not self.verbose:
                output = sys.stdout.getvalue()
                sys.stdout = original_stdout
                
                # Count results from output
                if 'Total tests:' in output:
                    for line in output.split('\n'):
                        if line.startswith('Total tests:'):
                            self.results[suite_name]['total'] = int(line.split(':')[1].strip())
                        elif line.startswith('Passed:'):
                            self.results[suite_name]['passed'] = int(line.split(':')[1].strip())
                        elif line.startswith('Failed:'):
                            self.results[suite_name]['failed'] = int(line.split(':')[1].strip())
                
                # Print summary only
                print(f"{suite_name.capitalize()}: {self.results[suite_name]['passed']}/{self.results[suite_name]['total']} passed")
            else:
                # In verbose mode, results are already printed
                pass
            
            return success
            
        except Exception as e:
            if not self.verbose:
                sys.stdout = original_stdout
            print(f"ERROR running {suite_name} tests: {e}")
            return False
    
    def run_all(self):
        """Run all test suites."""
        start_time = datetime.now()
        
        print("=" * 60)
        print("SISTEM PAKAR IKAN - TEST SUITE")
        print("=" * 60)
        print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run each suite
        results = {}
        results['core'] = self.run_suite('core', test_core)
        results['services'] = self.run_suite('services', test_services)
        results['integration'] = self.run_suite('integration', test_integration)
        
        # Overall summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("OVERALL TEST SUMMARY")
        print("=" * 60)
        
        total_all = sum(r['total'] for r in self.results.values())
        passed_all = sum(r['passed'] for r in self.results.values())
        failed_all = sum(r['failed'] for r in self.results.values())
        
        print(f"Total tests run: {total_all}")
        print(f"Passed: {passed_all} ({passed_all/total_all*100:.1f}%)")
        print(f"Failed: {failed_all}")
        print(f"Duration: {duration:.2f}s")
        
        # Suite breakdown
        print("\nBreakdown by suite:")
        for suite_name, result in self.results.items():
            if result['total'] > 0:
                status = "✅" if result['failed'] == 0 else "❌"
                print(f"  {status} {suite_name.capitalize():12} {result['passed']:2}/{result['total']:2} passed")
        
        # Final verdict
        print("\n" + "=" * 60)
        if all(results.values()):
            print("✅ ALL TESTS PASSED!")
            print("✅ Core and Services modules are working correctly and integrated!")
            return True
        else:
            print("❌ SOME TESTS FAILED")
            print("Please check the output above for details.")
            return False
    
    def run_single_suite(self, suite_name):
        """Run a specific test suite."""
        suite_map = {
            'core': test_core,
            'services': test_services,
            'integration': test_integration,
        }
        
        if suite_name not in suite_map:
            print(f"Error: Unknown suite '{suite_name}'")
            print(f"Available suites: {', '.join(suite_map.keys())}")
            return False
        
        return self.run_suite(suite_name, suite_map[suite_name])


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run test suite for Sistem Pakar Ikan')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--suite', '-s', type=str, choices=['core', 'services', 'integration', 'all'],
                        default='all', help='Which test suite to run')
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    
    if args.suite == 'all':
        success = runner.run_all()
    else:
        success = runner.run_single_suite(args.suite)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
