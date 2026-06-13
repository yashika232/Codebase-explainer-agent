import pytest
import tempfile
import shutil
from pathlib import Path
from repo_explainer.utils import get_repo_structure, read_safe_text
from repo_explainer.evaluator import setup_auth_repo, setup_math_repo

@pytest.fixture
def temp_sandbox():
    """Fixture providing a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

def test_setup_auth_repo(temp_sandbox):
    """Verifies that the auth repo setup writes the correct files."""
    setup_auth_repo(temp_sandbox)
    
    # Assert directories are created
    assert (temp_sandbox / "src" / "auth").exists()
    assert (temp_sandbox / "src" / "app").exists()
    assert (temp_sandbox / "config").exists()
    
    # Assert files exist
    assert (temp_sandbox / "config" / "settings.py").is_file()
    assert (temp_sandbox / "src" / "auth" / "hashing.py").is_file()
    assert (temp_sandbox / "src" / "auth" / "middleware.py").is_file()
    assert (temp_sandbox / "src" / "app" / "main.py").is_file()

def test_setup_math_repo(temp_sandbox):
    """Verifies that the math repo setup writes the correct files."""
    setup_math_repo(temp_sandbox)
    
    # Assert directories
    assert (temp_sandbox / "src" / "core").exists()
    assert (temp_sandbox / "src" / "cli").exists()
    
    # Assert files
    assert (temp_sandbox / "src" / "core" / "calculator.py").is_file()
    assert (temp_sandbox / "src" / "core" / "fibonacci.py").is_file()
    assert (temp_sandbox / "src" / "cli" / "parser.py").is_file()
    assert (temp_sandbox / "src" / "main.py").is_file()

def test_get_repo_structure(temp_sandbox):
    """Verifies the tree representation function works correctly."""
    # Create simple structure
    (temp_sandbox / "dir1").mkdir()
    with open(temp_sandbox / "dir1" / "file1.py", "w") as f:
        f.write("test")
    with open(temp_sandbox / "file2.txt", "w") as f:
        f.write("test")
        
    structure = get_repo_structure(temp_sandbox)
    
    # Assert output lists sub-items
    assert "dir1" in structure
    assert "file1.py" in structure
    assert "file2.txt" in structure

def test_read_safe_text(temp_sandbox):
    """Verifies reading safe text with encoding and truncation works."""
    file_path = temp_sandbox / "sample.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("A" * 100)
        
    # Read full file
    content = read_safe_text(file_path)
    assert content == "A" * 100
    
    # Read truncated
    content_truncated = read_safe_text(file_path, max_chars=10)
    assert len(content_truncated) > 10
    assert "... [TRUNCATED" in content_truncated
