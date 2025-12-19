"""
Comprehensive unit tests for CCDictionary class.

Tests cover:
- Dictionary loading and initialization
- All lookup methods
- Edge cases and error handling
- Performance and caching
- Metadata and statistics
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Import the CCDictionary class
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from cc_dictionary import CCDictionary, reset_dictionary


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_dictionary_data():
    """Sample dictionary data for testing."""
    return {
        "_metadata": {
            "source": "CC-CEDICT",
            "format_version": "1.0",
            "total_entries": 5
        },
        "学": {
            "simplified": "学",
            "traditional": "學",
            "pinyin": "xue2",
            "definitions": ["to learn", "to study", "learning", "science"]
        },
        "你": {
            "simplified": "你",
            "traditional": "你",
            "pinyin": "ni3",
            "definitions": ["you (informal)"]
        },
        "好": {
            "simplified": "好",
            "traditional": "好",
            "pinyin": "hao3",
            "definitions": ["good", "well", "proper"]
        },
        "中": {
            "simplified": "中",
            "traditional": "中",
            "pinyin": "zhong1",
            "definitions": ["middle", "center", "within"]
        },
        "國": {
            "simplified": "国",
            "traditional": "國",
            "pinyin": "guo2",
            "definitions": ["country", "nation", "state"]
        }
    }


@pytest.fixture
def sample_dict_file(sample_dictionary_data, tmp_path):
    """Create a temporary dictionary file for testing."""
    dict_file = tmp_path / "test_dict.json"
    with open(dict_file, 'w', encoding='utf-8') as f:
        json.dump(sample_dictionary_data, f, ensure_ascii=False)
    return str(dict_file)


@pytest.fixture
def dictionary(sample_dict_file):
    """Create a CCDictionary instance for testing."""
    return CCDictionary(sample_dict_file)


@pytest.fixture(autouse=True)
def reset_global_dictionary():
    """Reset global dictionary instance before each test."""
    reset_dictionary()
    yield
    reset_dictionary()


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

def test_initialization_success(sample_dict_file):
    """Test successful dictionary initialization."""
    dictionary = CCDictionary(sample_dict_file)
    assert dictionary is not None
    assert len(dictionary) == 5
    assert dictionary.entry_count == 5


def test_initialization_file_not_found():
    """Test initialization with non-existent file."""
    with pytest.raises(FileNotFoundError):
        CCDictionary("nonexistent_file.json")


def test_initialization_invalid_json(tmp_path):
    """Test initialization with invalid JSON."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{ invalid json }", encoding='utf-8')
    
    with pytest.raises(json.JSONDecodeError):
        CCDictionary(str(invalid_file))


def test_initialization_missing_required_fields(tmp_path):
    """Test initialization with missing required fields."""
    invalid_data = {
        "学": {
            "simplified": "学",
            # Missing: traditional, pinyin, definitions
        }
    }
    
    invalid_file = tmp_path / "invalid_structure.json"
    with open(invalid_file, 'w', encoding='utf-8') as f:
        json.dump(invalid_data, f)
    
    with pytest.raises(ValueError):
        CCDictionary(str(invalid_file))


def test_initialization_empty_dictionary(tmp_path):
    """Test initialization with empty dictionary."""
    empty_data = {"_metadata": {"source": "Test"}}
    empty_file = tmp_path / "empty.json"
    with open(empty_file, 'w', encoding='utf-8') as f:
        json.dump(empty_data, f)
    
    with pytest.raises(ValueError):
        CCDictionary(str(empty_file))


# ============================================================================
# LOOKUP METHOD TESTS
# ============================================================================

def test_lookup_existing_character(dictionary):
    """Test lookup for existing character."""
    entry = dictionary.lookup("学")
    assert entry is not None
    assert entry['simplified'] == "学"
    assert entry['traditional'] == "學"
    assert entry['pinyin'] == "xue2"
    assert len(entry['definitions']) == 4
    assert "to learn" in entry['definitions']


def test_lookup_nonexistent_character(dictionary):
    """Test lookup for non-existent character."""
    entry = dictionary.lookup("不存在")
    assert entry is None


def test_lookup_empty_string(dictionary):
    """Test lookup with empty string."""
    entry = dictionary.lookup("")
    assert entry is None


def test_lookup_none(dictionary):
    """Test lookup with None."""
    entry = dictionary.lookup(None)
    assert entry is None


def test_lookup_metadata_key(dictionary):
    """Test that metadata key is not returned as entry."""
    entry = dictionary.lookup("_metadata")
    assert entry is None


def test_lookup_caching(dictionary):
    """Test that lookup results are cached."""
    # First lookup
    entry1 = dictionary.lookup("学")
    
    # Get cache info
    cache_info = dictionary._cached_lookup.cache_info()
    hits_before = cache_info.hits
    misses_before = cache_info.misses
    
    # Second lookup (should hit cache)
    entry2 = dictionary.lookup("学")
    
    cache_info_after = dictionary._cached_lookup.cache_info()
    assert cache_info_after.hits > hits_before
    assert entry1 == entry2


# ============================================================================
# LOOKUP_CHARACTER METHOD TESTS
# ============================================================================

def test_lookup_character_existing(dictionary):
    """Test lookup_character for existing character."""
    meaning = dictionary.lookup_character("学")
    assert meaning == "to learn"


def test_lookup_character_nonexistent(dictionary):
    """Test lookup_character for non-existent character."""
    meaning = dictionary.lookup_character("不存在")
    assert meaning is None


def test_lookup_character_empty_definitions(tmp_path):
    """Test lookup_character with empty definitions list."""
    data = {
        "测": {
            "simplified": "测",
            "traditional": "測",
            "pinyin": "ce4",
            "definitions": []
        }
    }
    
    dict_file = tmp_path / "empty_defs.json"
    with open(dict_file, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    
    dictionary = CCDictionary(str(dict_file))
    meaning = dictionary.lookup_character("测")
    assert meaning is None


# ============================================================================
# LOOKUP_ENTRY METHOD TESTS
# ============================================================================

def test_lookup_entry_alias(dictionary):
    """Test that lookup_entry is an alias for lookup."""
    entry1 = dictionary.lookup("你")
    entry2 = dictionary.lookup_entry("你")
    assert entry1 == entry2


# ============================================================================
# HAS_ENTRY METHOD TESTS
# ============================================================================

def test_has_entry_existing(dictionary):
    """Test has_entry for existing character."""
    assert dictionary.has_entry("学") is True
    assert dictionary.has_entry("你") is True


def test_has_entry_nonexistent(dictionary):
    """Test has_entry for non-existent character."""
    assert dictionary.has_entry("不存在") is False


def test_has_entry_empty_string(dictionary):
    """Test has_entry with empty string."""
    assert dictionary.has_entry("") is False


def test_has_entry_none(dictionary):
    """Test has_entry with None."""
    assert dictionary.has_entry(None) is False


def test_has_entry_metadata(dictionary):
    """Test has_entry excludes metadata."""
    assert dictionary.has_entry("_metadata") is False


def test_contains_operator(dictionary):
    """Test 'in' operator (uses __contains__)."""
    assert "学" in dictionary
    assert "不存在" not in dictionary


# ============================================================================
# GET_PINYIN METHOD TESTS
# ============================================================================

def test_get_pinyin_existing(dictionary):
    """Test get_pinyin for existing character."""
    pinyin = dictionary.get_pinyin("学")
    assert pinyin == "xue2"


def test_get_pinyin_nonexistent(dictionary):
    """Test get_pinyin for non-existent character."""
    pinyin = dictionary.get_pinyin("不存在")
    assert pinyin is None


# ============================================================================
# GET_DEFINITIONS METHOD TESTS
# ============================================================================

def test_get_definitions_existing(dictionary):
    """Test get_definitions for existing character."""
    definitions = dictionary.get_definitions("学")
    assert isinstance(definitions, list)
    assert len(definitions) == 4
    assert "to learn" in definitions


def test_get_definitions_nonexistent(dictionary):
    """Test get_definitions for non-existent character."""
    definitions = dictionary.get_definitions("不存在")
    assert definitions == []


# ============================================================================
# GET_TRADITIONAL METHOD TESTS
# ============================================================================

def test_get_traditional_existing(dictionary):
    """Test get_traditional for existing simplified character."""
    traditional = dictionary.get_traditional("学")
    assert traditional == "學"


def test_get_traditional_same_as_simplified(dictionary):
    """Test get_traditional when traditional equals simplified."""
    traditional = dictionary.get_traditional("你")
    assert traditional == "你"


def test_get_traditional_nonexistent(dictionary):
    """Test get_traditional for non-existent character."""
    traditional = dictionary.get_traditional("不存在")
    assert traditional is None


# ============================================================================
# GET_SIMPLIFIED METHOD TESTS
# ============================================================================

def test_get_simplified_from_traditional(dictionary):
    """Test get_simplified from traditional character."""
    simplified = dictionary.get_simplified("國")
    assert simplified == "国"


def test_get_simplified_same_as_traditional(dictionary):
    """Test get_simplified when simplified equals traditional."""
    simplified = dictionary.get_simplified("你")
    assert simplified == "你"


def test_get_simplified_nonexistent(dictionary):
    """Test get_simplified for non-existent character."""
    simplified = dictionary.get_simplified("不存在的字")
    assert simplified is None


# ============================================================================
# BATCH_LOOKUP METHOD TESTS
# ============================================================================

def test_batch_lookup_success(dictionary):
    """Test batch lookup with multiple characters."""
    characters = ["学", "你", "好"]
    results = dictionary.batch_lookup(characters)
    
    assert len(results) == 3
    assert "学" in results
    assert "你" in results
    assert "好" in results
    assert results["学"] is not None
    assert results["你"] is not None
    assert results["好"] is not None


def test_batch_lookup_mixed(dictionary):
    """Test batch lookup with mix of existing and non-existent."""
    characters = ["学", "不存在", "你"]
    results = dictionary.batch_lookup(characters)
    
    assert len(results) == 3
    assert results["学"] is not None
    assert results["不存在"] is None
    assert results["你"] is not None


def test_batch_lookup_empty_list(dictionary):
    """Test batch lookup with empty list."""
    results = dictionary.batch_lookup([])
    assert results == {}


# ============================================================================
# METADATA AND STATISTICS TESTS
# ============================================================================

def test_get_metadata(dictionary):
    """Test get_metadata returns correct metadata."""
    metadata = dictionary.get_metadata()
    assert isinstance(metadata, dict)
    assert metadata['source'] == "CC-CEDICT"
    assert metadata['format_version'] == "1.0"
    assert metadata['total_entries'] == 5


def test_get_stats(dictionary):
    """Test get_stats returns statistics."""
    stats = dictionary.get_stats()
    
    assert 'entry_count' in stats
    assert 'cache_hits' in stats
    assert 'cache_misses' in stats
    assert 'cache_size' in stats
    assert 'cache_maxsize' in stats
    assert 'metadata' in stats
    
    assert stats['entry_count'] == 5
    assert stats['cache_maxsize'] == 2000  # Updated cache size for better performance


def test_get_stats_after_lookups(dictionary):
    """Test get_stats cache info after some lookups."""
    # Do some lookups
    dictionary.lookup("学")
    dictionary.lookup("学")  # Cache hit
    dictionary.lookup("你")
    
    stats = dictionary.get_stats()
    assert stats['cache_hits'] >= 1  # At least one cache hit
    assert stats['cache_misses'] >= 2  # At least two cache misses


# ============================================================================
# CACHE MANAGEMENT TESTS
# ============================================================================

def test_clear_cache(dictionary):
    """Test clear_cache clears the LRU cache."""
    # Do some lookups to populate cache
    dictionary.lookup("学")
    dictionary.lookup("你")
    
    # Get cache size before clear
    stats_before = dictionary.get_stats()
    cache_size_before = stats_before['cache_size']
    
    # Clear cache
    dictionary.clear_cache()
    
    # Check cache is cleared
    stats_after = dictionary.get_stats()
    assert stats_after['cache_size'] == 0
    assert stats_after['cache_hits'] == 0
    assert stats_after['cache_misses'] == 0


def test_log_performance_stats(dictionary):
    """Test log_performance_stats logs statistics."""
    # Do some lookups to generate stats
    dictionary.lookup("学")
    dictionary.lookup("学")  # Cache hit
    dictionary.lookup("你")
    
    # Should not raise any exceptions
    try:
        dictionary.log_performance_stats(level="info")
        dictionary.log_performance_stats(level="debug")
        assert True
    except Exception as e:
        pytest.fail(f"log_performance_stats raised exception: {e}")


# ============================================================================
# SPECIAL METHOD TESTS (__len__, __contains__, __repr__)
# ============================================================================

def test_len_operator(dictionary):
    """Test __len__ returns correct count."""
    assert len(dictionary) == 5


def test_repr(dictionary):
    """Test __repr__ returns informative string."""
    repr_str = repr(dictionary)
    assert "CCDictionary" in repr_str
    assert "entries=5" in repr_str
    assert "CC-CEDICT" in repr_str


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_workflow(dictionary):
    """Test complete workflow with dictionary."""
    # Check character exists
    assert "学" in dictionary
    
    # Get full entry
    entry = dictionary.lookup("学")
    assert entry is not None
    
    # Get individual components
    pinyin = dictionary.get_pinyin("学")
    definitions = dictionary.get_definitions("学")
    traditional = dictionary.get_traditional("学")
    
    assert pinyin == "xue2"
    assert len(definitions) > 0
    assert traditional == "學"
    
    # Get statistics
    stats = dictionary.get_stats()
    assert stats['entry_count'] == 5


def test_multiple_lookups_performance(dictionary):
    """Test performance of multiple lookups."""
    # First pass (cache misses)
    for char in ["学", "你", "好", "中"]:
        dictionary.lookup(char)
    
    stats_after_first = dictionary.get_stats()
    misses_first = stats_after_first['cache_misses']
    
    # Second pass (cache hits)
    for char in ["学", "你", "好", "中"]:
        dictionary.lookup(char)
    
    stats_after_second = dictionary.get_stats()
    hits_second = stats_after_second['cache_hits']
    
    # Should have more hits than misses after second pass
    assert hits_second >= 4


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_corrupted_entry_handling(tmp_path):
    """Test handling of corrupted dictionary entry."""
    corrupted_data = {
        "测": "not a dictionary"  # Should be a dict
    }
    
    corrupted_file = tmp_path / "corrupted.json"
    with open(corrupted_file, 'w', encoding='utf-8') as f:
        json.dump(corrupted_data, f)
    
    with pytest.raises(ValueError):
        CCDictionary(str(corrupted_file))


def test_invalid_definitions_type(tmp_path):
    """Test handling of invalid definitions type."""
    invalid_data = {
        "测": {
            "simplified": "测",
            "traditional": "測",
            "pinyin": "ce4",
            "definitions": "not a list"  # Should be a list
        }
    }
    
    invalid_file = tmp_path / "invalid_defs.json"
    with open(invalid_file, 'w', encoding='utf-8') as f:
        json.dump(invalid_data, f)
    
    with pytest.raises(ValueError):
        CCDictionary(str(invalid_file))


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

def test_whitespace_character_lookup(dictionary):
    """Test lookup with whitespace characters."""
    assert dictionary.lookup(" ") is None
    assert dictionary.lookup("\n") is None
    assert dictionary.lookup("\t") is None


def test_special_characters_lookup(dictionary):
    """Test lookup with special characters."""
    assert dictionary.lookup("!@#$%") is None
    assert dictionary.lookup("123") is None


def test_very_long_string_lookup(dictionary):
    """Test lookup with very long string."""
    long_string = "很长的字符串" * 100
    result = dictionary.lookup(long_string)
    assert result is None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

