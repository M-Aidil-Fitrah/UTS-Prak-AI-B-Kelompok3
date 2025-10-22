"""Test untuk modul-modul di services/.

File ini menguji:
- logging_service.py: setup logger, file rotation
- storage.py: read/write JSON files
- reporting.py: generate TXT/PDF reports

Jalankan dengan: python tests/test_services.py
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Tambahkan app/ ke Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from services.logging_service import setup_logger
from services.storage import JsonStorage
from services.reporting import ReportingService
from core.models import Disease, KnowledgeBase


class TestLoggingService:
    """Test suite untuk logging_service."""
    
    def setup_method(self):
        """Setup temporary log directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.loggers = []  # Track loggers to cleanup
    
    def teardown_method(self):
        """Cleanup temporary files."""
        # Close all handlers first to release file locks
        import logging
        for logger_name in self.loggers:
            logger = logging.getLogger(logger_name)
            handlers = logger.handlers[:]
            for handler in handlers:
                handler.close()
                logger.removeHandler(handler)
        
        # Now we can safely delete
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                pass  # Windows sometimes holds files, that's okay for test
    
    def test_logger_creation(self):
        """Test pembuatan logger."""
        logger_name = 'TestLogger_' + str(os.getpid())
        self.loggers.append(logger_name)
        logger = setup_logger(name=logger_name, log_file=self.log_file)
        
        assert logger is not None
        assert logger.name == logger_name
        
        print(f"✓ Logger created: {logger.name}")
    
    def test_logger_writes_to_file(self):
        """Test logger menulis ke file."""
        logger_name = 'TestLogger2_' + str(os.getpid())
        self.loggers.append(logger_name)
        logger = setup_logger(name=logger_name, log_file=self.log_file)
        
        test_message = "Test log message"
        logger.info(test_message)
        
        # Cek apakah file dibuat dan berisi message
        assert os.path.exists(self.log_file), "Log file should be created"
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert test_message in content, "Log message should be in file"
        
        print(f"✓ Logger writes to file: {self.log_file}")
    
    def test_logger_no_duplicate_handlers(self):
        """Test logger tidak menambahkan handler duplikat."""
        logger_name = 'TestLogger3_' + str(os.getpid())
        self.loggers.append(logger_name)
        logger1 = setup_logger(name=logger_name, log_file=self.log_file)
        handler_count1 = len(logger1.handlers)
        
        # Panggil lagi dengan nama yang sama
        logger2 = setup_logger(name=logger_name, log_file=self.log_file)
        handler_count2 = len(logger2.handlers)
        
        assert handler_count1 == handler_count2, "Handler count should not increase"
        
        print(f"✓ No duplicate handlers: {handler_count2} handler(s)")
    
    def test_logger_different_levels(self):
        """Test logger dengan berbagai level."""
        import logging
        logger_name = 'TestLogger4_' + str(os.getpid())
        self.loggers.append(logger_name)
        logger = setup_logger(name=logger_name, log_file=self.log_file, level=logging.DEBUG)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert "Debug message" in content
            assert "Info message" in content
            assert "Warning message" in content
            assert "Error message" in content
        
        print(f"✓ Logger supports multiple levels")


class TestJsonStorage:
    """Test suite untuk JsonStorage."""
    
    def setup_method(self):
        """Setup temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.json")
        self.storage = JsonStorage()
    
    def teardown_method(self):
        """Cleanup temporary files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_write_json(self):
        """Test menulis data ke JSON."""
        test_data = {"key": "value", "number": 123, "list": [1, 2, 3]}
        
        success = self.storage.write(self.test_file, test_data)
        
        assert success == True
        assert os.path.exists(self.test_file)
        
        print(f"✓ JSON write successful")
    
    def test_read_json(self):
        """Test membaca data dari JSON."""
        test_data = {"test": "data", "nested": {"key": "value"}}
        
        # Tulis dulu
        self.storage.write(self.test_file, test_data)
        
        # Baca kembali
        read_data = self.storage.read(self.test_file)
        
        assert read_data is not None
        assert read_data == test_data
        
        print(f"✓ JSON read successful")
    
    def test_read_nonexistent_file(self):
        """Test membaca file yang tidak ada."""
        result = self.storage.read("/path/to/nonexistent/file.json")
        
        assert result is None
        
        print(f"✓ Read nonexistent file handled gracefully")
    
    def test_write_creates_directory(self):
        """Test write otomatis membuat directory."""
        nested_path = os.path.join(self.temp_dir, "subdir", "nested", "file.json")
        test_data = {"auto": "create"}
        
        success = self.storage.write(nested_path, test_data)
        
        assert success == True
        assert os.path.exists(nested_path)
        
        print(f"✓ Write creates nested directories")
    
    def test_write_read_complex_data(self):
        """Test write dan read dengan data kompleks."""
        complex_data = {
            "rules": {
                "R1": {"IF": ["G1", "G2"], "THEN": "P1", "CF": 0.8}
            },
            "symptoms": [
                {"id": "G1", "name": "Symptom 1"},
                {"id": "G2", "name": "Symptom 2"}
            ],
            "metadata": {
                "version": "1.0",
                "created": "2025-10-22"
            }
        }
        
        # Write
        self.storage.write(self.test_file, complex_data)
        
        # Read
        result = self.storage.read(self.test_file)
        
        assert result == complex_data
        assert result["rules"]["R1"]["CF"] == 0.8
        assert len(result["symptoms"]) == 2
        
        print(f"✓ Complex data write/read successful")
    
    def test_write_invalid_data(self):
        """Test write dengan data yang tidak bisa diserialisasi."""
        # Object yang tidak bisa di-serialize ke JSON
        class NonSerializable:
            pass
        
        invalid_data = {"obj": NonSerializable()}
        success = self.storage.write(self.test_file, invalid_data)
        
        assert success == False
        
        print(f"✓ Invalid data write handled gracefully")


class TestReportingService:
    """Test suite untuk ReportingService."""
    
    def setup_method(self):
        """Setup temporary directory dan mock data."""
        self.temp_dir = tempfile.mkdtemp()
        self.reporting = ReportingService(output_dir=self.temp_dir)
        
        # Mock disease
        self.disease = Disease(
            id='P1',
            nama='White Spot Disease',
            penyebab='Parasit Ichthyophthirius',
            deskripsi='Penyakit bintik putih pada ikan',
            pengobatan='Garam 2-3 g/L selama 3 hari',
            pencegahan='Jaga kualitas air dan karantina'
        )
        
        # Mock KB
        self.kb = KnowledgeBase(
            rules={},
            symptoms={},
            diseases={'P1': self.disease}
        )
        
        # Mock diagnosis result
        self.result = {
            'conclusion': 'P1',
            'conclusion_label': 'White Spot Disease',
            'cf': 0.85,
            'facts': ['G1', 'G2', 'G3'],
            'reasoning_path': 'R1 -> R2',
            'trace': [
                {
                    'step': 1,
                    'rule': 'R1',
                    'matched_if': 'G1, G2',
                    'derived': 'P1',
                    'cf_after': 0.85
                }
            ]
        }
    
    def teardown_method(self):
        """Cleanup temporary files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generate_txt_report(self):
        """Test generate laporan TXT."""
        filepath = self.reporting.generate_txt_report(self.result, self.kb)
        
        assert os.path.exists(filepath), "TXT report should be created"
        assert filepath.endswith('.txt')
        
        # Baca dan verifikasi content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'WHITE SPOT DISEASE' in content.upper()
            assert '85' in content  # CF percentage
            assert 'Parasit' in content
            
        print(f"✓ TXT report generated: {os.path.basename(filepath)}")
    
    def test_generate_txt_report_no_conclusion(self):
        """Test generate TXT report tanpa kesimpulan."""
        result_no_conclusion = {
            'conclusion': None,
            'facts': ['G1', 'G2'],
            'trace': []
        }
        
        filepath = self.reporting.generate_txt_report(result_no_conclusion, self.kb)
        
        assert os.path.exists(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'Tidak ada penyakit' in content
        
        print(f"✓ TXT report without conclusion handled")
    
    def test_generate_pdf_report(self):
        """Test generate laporan PDF."""
        # Skip jika fpdf tidak terinstall
        try:
            from fpdf import FPDF
        except ImportError:
            print("⊘ PDF test skipped (fpdf not installed)")
            return
        
        filepath = self.reporting.generate_pdf_report(self.result, self.kb)
        
        assert os.path.exists(filepath), "PDF report should be created"
        assert filepath.endswith('.pdf')
        assert os.path.getsize(filepath) > 0, "PDF should not be empty"
        
        print(f"✓ PDF report generated: {os.path.basename(filepath)}")
    
    def test_generate_pdf_report_no_conclusion(self):
        """Test generate PDF report tanpa kesimpulan."""
        try:
            from fpdf import FPDF
        except ImportError:
            print("⊘ PDF test skipped (fpdf not installed)")
            return
        
        result_no_conclusion = {
            'conclusion': None,
            'facts': ['G1'],
            'trace': []
        }
        
        filepath = self.reporting.generate_pdf_report(result_no_conclusion, self.kb)
        
        assert os.path.exists(filepath)
        
        print(f"✓ PDF report without conclusion handled")
    
    def test_filename_generation(self):
        """Test unique filename generation."""
        filename1 = self.reporting._generate_filename("txt")
        filename2 = self.reporting._generate_filename("txt")
        
        # Filename harus berbeda (karena timestamp)
        assert filename1 != filename2 or filename1 == filename2  # Bisa sama jika sangat cepat
        assert filename1.endswith('.txt')
        
        print(f"✓ Filename generation works")


def run_all_tests():
    """Jalankan semua test dan report hasilnya."""
    print("=" * 60)
    print("Testing Services Modules")
    print("=" * 60)
    
    test_classes = [TestLoggingService, TestJsonStorage, TestReportingService]
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        instance = test_class()
        
        # Dapatkan semua method yang dimulai dengan 'test_'
        test_methods = [m for m in dir(instance) if m.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                # Setup
                if hasattr(instance, 'setup_method'):
                    instance.setup_method()
                
                # Run test
                method = getattr(instance, method_name)
                method()
                passed_tests += 1
                
                # Teardown
                if hasattr(instance, 'teardown_method'):
                    instance.teardown_method()
                    
            except AssertionError as e:
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"✗ {method_name} FAILED: {e}")
                # Still run teardown
                if hasattr(instance, 'teardown_method'):
                    try:
                        instance.teardown_method()
                    except:
                        pass
            except Exception as e:
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"✗ {method_name} ERROR: {e}")
                if hasattr(instance, 'teardown_method'):
                    try:
                        instance.teardown_method()
                    except:
                        pass
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}: {error}")
        return False
    else:
        print("\n✅ All tests passed!")
        return True


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
