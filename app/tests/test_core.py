"""Test untuk modul-modul di core/.

File ini menguji:
- inference_engine.py: forward/backward chaining, CF calculation
- search_filter.py: search dan filter functions
- models.py: dataclass structures

Jalankan dengan: python -m pytest tests/test_core.py -v
Atau: python tests/test_core.py (standalone)
"""

import sys
from pathlib import Path

# Tambahkan app/ ke Python path agar bisa import module
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from core.inference_engine import InferenceEngine, _combine_cf, _antecedent_cf
from core.search_filter import (
    search_symptoms, search_diseases, search_rules,
    get_rules_by_symptom, get_rules_by_disease,
    get_possible_diseases, get_related_symptoms
)
from core.models import Symptom, Disease, Rule, Fact, DiagnosisResult, KnowledgeBase


class TestInferenceEngine:
    """Test suite untuk InferenceEngine."""
    
    def setup_method(self):
        """Setup test data sebelum setiap test method."""
        self.engine = InferenceEngine(threshold=0.5)
        self.test_rules = {
            'R1': {'IF': ['G1', 'G2'], 'THEN': 'P1', 'CF': 0.8},
            'R2': {'IF': ['G2', 'G3'], 'THEN': 'P2', 'CF': 0.7},
            'R3': {'IF': ['P1', 'G3'], 'THEN': 'P3', 'CF': 0.9},
        }
        self.test_facts = {'G1': 1.0, 'G2': 0.9, 'G3': 0.8}
    
    def test_cf_combination(self):
        """Test kombinasi CF menggunakan formula MYCIN."""
        # CF_new = CF_old + CF_new * (1 - CF_old)
        result = _combine_cf(0.6, 0.5)
        expected = 0.6 + 0.5 * (1 - 0.6)  # = 0.6 + 0.2 = 0.8
        assert abs(result - expected) < 0.001, f"Expected {expected}, got {result}"
        print(f"✓ Test CF combination: {result:.3f}")
    
    def test_antecedent_cf(self):
        """Test agregasi CF antecedent (MIN untuk konjungsi)."""
        cfs = [0.8, 0.9, 0.7]
        result = _antecedent_cf(cfs)
        assert result == 0.7, f"Expected 0.7 (min), got {result}"
        print(f"✓ Test antecedent CF (MIN): {result}")
    
    def test_forward_chaining_basic(self):
        """Test forward chaining dasar."""
        result = self.engine.forward_chaining(self.test_rules, self.test_facts)
        
        assert result['method'] == 'forward'
        assert 'P1' in result['conclusions'], "P1 harus diturunkan dari G1+G2"
        assert len(result['used_rules']) > 0, "Harus ada rules yang terpakai"
        assert len(result['trace']) > 0, "Harus ada trace steps"
        
        print(f"✓ Forward chaining: {len(result['used_rules'])} rules fired")
        print(f"  Conclusions: {list(result['conclusions'].keys())}")
    
    def test_forward_chaining_chained_rules(self):
        """Test forward chaining dengan rules berantai."""
        result = self.engine.forward_chaining(self.test_rules, self.test_facts)
        
        # R1 harus fire (G1+G2 -> P1), lalu R3 harus fire (P1+G3 -> P3)
        assert 'P1' in result['conclusions']
        assert 'P3' in result['conclusions'], "P3 harus diturunkan dari P1+G3"
        
        print(f"✓ Chained inference: P1 → P3")
        print(f"  Reasoning path: {result['reasoning_path']}")
    
    def test_backward_chaining_basic(self):
        """Test backward chaining dasar."""
        result = self.engine.backward_chaining(self.test_rules, self.test_facts, 'P1')
        
        assert result['method'] == 'backward'
        assert result['success'] == True, "P1 harus bisa dibuktikan dari G1+G2"
        assert result['goal'] == 'P1'
        assert result['cf'] > 0
        
        print(f"✓ Backward chaining: goal P1 proved with CF={result['cf']:.3f}")
    
    def test_backward_chaining_failure(self):
        """Test backward chaining yang gagal (goal tidak bisa dibuktikan)."""
        facts = {'G1': 1.0}  # Hanya G1, tidak cukup untuk P1 yang butuh G1+G2
        result = self.engine.backward_chaining(self.test_rules, facts, 'P1')
        
        assert result['success'] == False, "P1 tidak bisa dibuktikan hanya dengan G1"
        print(f"✓ Backward chaining failure handled correctly")
    
    def test_diagnose_pipeline(self):
        """Test diagnose() method (end-to-end pipeline)."""
        # Mock KB
        class MockKB:
            def __init__(self):
                self.rules = {
                    'R1': {'IF': ['S1', 'S2'], 'THEN': 'D1', 'CF': 0.8, 'recommendation': 'Test treatment'}
                }
                self.symptoms = {
                    'S1': {'id': 'S1', 'name': 'Symptom 1', 'weight': 1.0},
                    'S2': {'id': 'S2', 'name': 'Symptom 2', 'weight': 0.9}
                }
                self.diseases = {
                    'D1': {
                        'id': 'D1', 'name': 'Disease 1', 'nama': 'Penyakit 1',
                        'prevention': ['Wash hands'], 'treatments': ['Rest']
                    }
                }
        
        kb = MockKB()
        result = self.engine.diagnose(['S1', 'S2'], user_cf=0.9, kb=kb)
        
        assert 'conclusion' in result
        assert result['conclusion'] == 'D1'
        assert 'cf' in result
        assert 'trace' in result
        assert len(result['trace']) > 0
        
        print(f"✓ Diagnose pipeline: {result['conclusion']} with CF={result['cf']}")


class TestSearchFilter:
    """Test suite untuk search_filter."""
    
    def setup_method(self):
        """Setup test data."""
        self.symptoms = {
            'G1': {'id': 'G1', 'name': 'Bintik Putih', 'description': 'Bintik putih di tubuh', 'weight': 1.0, 'species': ['Lele', 'Nila']},
            'G2': {'id': 'G2', 'name': 'Nafsu Makan Turun', 'description': 'Ikan tidak mau makan', 'weight': 0.9, 'species': []},
            'G3': {'id': 'G3', 'name': 'Insang Pucat', 'description': 'Warna insang tidak normal', 'weight': 0.95, 'species': ['Nila']},
        }
        
        self.diseases = {
            'P1': {'id': 'P1', 'name': 'White Spot', 'nama': 'Bintik Putih', 'description': 'Infeksi parasit'},
            'P2': {'id': 'P2', 'name': 'BGD', 'nama': 'Penyakit Insang', 'description': 'Infeksi bakteri insang'},
        }
        
        self.rules = {
            'R1': {'IF': ['G1', 'G2'], 'THEN': 'P1', 'CF': 0.8, 'ask_why': 'Bintik putih khas'},
            'R2': {'IF': ['G2', 'G3'], 'THEN': 'P2', 'CF': 0.7},
            'R3': {'IF': ['G1'], 'THEN': 'P1', 'CF': 0.6},
        }
    
    def test_search_symptoms_by_query(self):
        """Test pencarian gejala berdasarkan text query."""
        results = search_symptoms(self.symptoms, query="putih")
        
        assert len(results) == 1
        assert results[0]['id'] == 'G1'
        
        print(f"✓ Search symptoms by query: found {len(results)} result(s)")
    
    def test_search_symptoms_by_species(self):
        """Test filter gejala berdasarkan spesies."""
        results = search_symptoms(self.symptoms, species_filter=['Nila'])
        
        # G1 (Lele+Nila) dan G3 (Nila) harus muncul, G2 (tidak ada species) juga muncul
        ids = [r['id'] for r in results]
        assert 'G1' in ids
        assert 'G3' in ids
        
        print(f"✓ Filter by species: {len(results)} symptoms for Nila")
    
    def test_search_symptoms_by_weight(self):
        """Test filter gejala berdasarkan weight range."""
        results = search_symptoms(self.symptoms, weight_min=0.9)
        
        # G1 (1.0), G3 (0.95) harus ada, G2 (0.9) boundary case
        assert len(results) >= 2
        
        print(f"✓ Filter by weight (>=0.9): {len(results)} symptoms")
    
    def test_search_diseases(self):
        """Test pencarian penyakit."""
        results = search_diseases(self.diseases, query="insang")
        
        assert len(results) == 1
        assert results[0]['id'] == 'P2'
        
        print(f"✓ Search diseases: found '{results[0]['name']}'")
    
    def test_search_rules_by_antecedent(self):
        """Test cari rules berdasarkan antecedent."""
        results = search_rules(self.rules, antecedent_filter='G1')
        
        # R1 dan R3 punya G1 di IF
        assert len(results) == 2
        ids = [r['id'] for r in results]
        assert 'R1' in ids
        assert 'R3' in ids
        
        print(f"✓ Search rules by antecedent G1: {len(results)} rules")
    
    def test_search_rules_by_consequent(self):
        """Test cari rules berdasarkan consequent."""
        results = search_rules(self.rules, consequent_filter='P1')
        
        # R1 dan R3 menghasilkan P1
        assert len(results) == 2
        
        print(f"✓ Search rules by consequent P1: {len(results)} rules")
    
    def test_search_rules_by_cf_range(self):
        """Test filter rules berdasarkan CF."""
        results = search_rules(self.rules, cf_min=0.7, cf_max=0.8)
        
        # R1 (0.8) dan R2 (0.7) dalam range
        assert len(results) == 2
        
        print(f"✓ Filter rules by CF (0.7-0.8): {len(results)} rules")
    
    def test_get_rules_by_symptom(self):
        """Test helper function get_rules_by_symptom."""
        results = get_rules_by_symptom(self.rules, 'G2')
        
        # R1 dan R2 punya G2
        assert len(results) == 2
        
        print(f"✓ Get rules by symptom G2: {len(results)} rules")
    
    def test_get_rules_by_disease(self):
        """Test helper function get_rules_by_disease."""
        results = get_rules_by_disease(self.rules, 'P1')
        
        assert len(results) == 2
        
        print(f"✓ Get rules by disease P1: {len(results)} rules")
    
    def test_get_possible_diseases(self):
        """Test prediksi penyakit yang mungkin dari gejala."""
        possible = get_possible_diseases(self.rules, ['G1', 'G2'])
        
        # Dari G1+G2, bisa P1 (dari R1) dan P2 (dari R2)
        assert 'P1' in possible
        assert 'P2' in possible
        
        print(f"✓ Get possible diseases from G1+G2: {possible}")
    
    def test_get_related_symptoms(self):
        """Test cari gejala terkait."""
        related = get_related_symptoms(self.rules, 'G1')
        
        # G1 muncul dengan G2 di R1, jadi G2 adalah related
        assert 'G2' in related
        
        print(f"✓ Related symptoms to G1: {related}")


class TestModels:
    """Test suite untuk models (dataclasses)."""
    
    def test_symptom_creation(self):
        """Test pembuatan object Symptom."""
        s = Symptom(id='G1', name='Test Symptom', question='Ada gejala?')
        
        assert s.id == 'G1'
        assert s.name == 'Test Symptom'
        
        print(f"✓ Symptom model: {s.id}")
    
    def test_disease_creation(self):
        """Test pembuatan object Disease."""
        d = Disease(
            id='P1',
            nama='Test Disease',
            penyebab='Virus',
            deskripsi='Test desc',
            pengobatan='Test treatment',
            pencegahan='Test prevention'
        )
        
        assert d.id == 'P1'
        assert d.nama == 'Test Disease'
        
        print(f"✓ Disease model: {d.id}")
    
    def test_rule_creation(self):
        """Test pembuatan object Rule."""
        r = Rule(id='R1', IF=['G1', 'G2'], THEN='P1', CF=0.8)
        
        assert r.id == 'R1'
        assert len(r.IF) == 2
        assert r.CF == 0.8
        
        print(f"✓ Rule model: {r.id}")
    
    def test_diagnosis_result_creation(self):
        """Test pembuatan DiagnosisResult dengan confidence percent."""
        disease = Disease('P1', 'Test', 'Cause', 'Desc', 'Treatment', 'Prevention')
        result = DiagnosisResult(disease=disease, final_cf=0.85, reasoning_path=[])
        
        assert result.final_cf == 0.85
        assert result.confidence_percent == 85.0
        
        print(f"✓ DiagnosisResult: CF={result.final_cf}, {result.confidence_percent}%")
    
    def test_knowledge_base_creation(self):
        """Test pembuatan KnowledgeBase container."""
        kb = KnowledgeBase(rules={}, symptoms={}, diseases={})
        
        assert isinstance(kb.rules, dict)
        assert isinstance(kb.symptoms, dict)
        assert isinstance(kb.diseases, dict)
        
        print(f"✓ KnowledgeBase model created")


def run_all_tests():
    """Jalankan semua test dan report hasilnya."""
    print("=" * 60)
    print("Testing Core Modules")
    print("=" * 60)
    
    test_classes = [TestInferenceEngine, TestSearchFilter, TestModels]
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
                # Setup jika ada
                if hasattr(instance, 'setup_method'):
                    instance.setup_method()
                
                # Jalankan test
                method = getattr(instance, method_name)
                method()
                passed_tests += 1
                
            except AssertionError as e:
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"✗ {method_name} FAILED: {e}")
            except Exception as e:
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"✗ {method_name} ERROR: {e}")
    
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
