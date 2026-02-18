"""
OCR Setup Checker

Run this script to check if all OCR dependencies are properly installed.
"""

import sys
import os

def check_python_packages():
    """Check if required Python packages are installed"""
    print("\n📦 Checking Python Packages...")
    print("-" * 60)
    
    packages = {
        'pytesseract': 'Tesseract OCR Python wrapper',
        'pdf2image': 'PDF to image converter',
        'PIL': 'Python Imaging Library (Pillow)'
    }
    
    all_installed = True
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"  ✅ {package:15} - {description}")
        except ImportError:
            print(f"  ❌ {package:15} - {description} (NOT INSTALLED)")
            all_installed = False
    
    if not all_installed:
        print("\n  Install missing packages:")
        print("  pip install pytesseract pdf2image Pillow")
    
    return all_installed

def check_tesseract():
    """Check if Tesseract OCR executable is installed"""
    print("\n🔍 Checking Tesseract OCR Executable...")
    print("-" * 60)
    
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Tesseract-OCR\tesseract.exe',
    ]
    
    found = False
    for path in tesseract_paths:
        if os.path.exists(path):
            print(f"  ✅ Found: {path}")
            found = True
            
            # Try to get version
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = path
                version = pytesseract.get_tesseract_version()
                print(f"  📌 Version: {version}")
            except:
                pass
            break
    
    if not found:
        print("  ❌ Tesseract executable not found in standard locations")
        print("\n  Download and install from:")
        print("  https://github.com/UB-Mannheim/tesseract/wiki")
        print("\n  Recommended: Install to C:\\Program Files\\Tesseract-OCR")
    
    return found

def check_poppler():
    """Check if Poppler is installed (needed by pdf2image)"""
    print("\n📄 Checking Poppler (PDF renderer)...")
    print("-" * 60)
    
    poppler_paths = [
        r'C:\Program Files\poppler\Library\bin',
        r'C:\Program Files (x86)\poppler\Library\bin',
        r'C:\poppler\Library\bin',
        r'C:\poppler-24.02.0\Library\bin',
        r'C:\Program Files\poppler-24.02.0\Library\bin',
    ]
    
    found = False
    for path in poppler_paths:
        if os.path.exists(path):
            print(f"  ✅ Found: {path}")
            
            # Check for pdftoppm.exe
            pdftoppm = os.path.join(path, 'pdftoppm.exe')
            if os.path.exists(pdftoppm):
                print(f"  ✅ pdftoppm.exe exists")
            
            found = True
            break
    
    if not found:
        print("  ❌ Poppler not found in standard locations")
        print("\n  Download and install from:")
        print("  https://github.com/oschwartz10612/poppler-windows/releases/")
        print("\n  Steps:")
        print("  1. Download latest release (e.g., Release-24.02.0-0.zip)")
        print("  2. Extract to C:\\poppler")
        print("  3. Ensure C:\\poppler\\Library\\bin exists")
        print("  4. (Optional) Add to system PATH")
    
    return found

def test_ocr():
    """Test OCR functionality with a simple example"""
    print("\n🧪 Testing OCR Functionality...")
    print("-" * 60)
    
    try:
        import pytesseract
        from PIL import Image
        import io
        
        # Create a simple test image with text
        from PIL import ImageDraw, ImageFont
        
        img = Image.new('RGB', (200, 50), color='white')
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Hello OCR", fill='black')
        
        # Test OCR
        text = pytesseract.image_to_string(img)
        
        if "hello" in text.lower() or "ocr" in text.lower():
            print("  ✅ OCR test successful!")
            print(f"  Extracted: {text.strip()}")
            return True
        else:
            print("  ⚠️  OCR test returned unexpected result:")
            print(f"  Result: {text}")
            return False
            
    except Exception as e:
        print(f"  ❌ OCR test failed: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("  OCR SETUP CHECKER")
    print("=" * 60)
    
    packages_ok = check_python_packages()
    tesseract_ok = check_tesseract()
    poppler_ok = check_poppler()
    
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    if packages_ok and tesseract_ok and poppler_ok:
        print("\n  ✅ All OCR dependencies are installed!")
        print("  Running functionality test...\n")
        
        if test_ocr():
            print("\n  🎉 OCR is fully functional!")
        else:
            print("\n  ⚠️  OCR components installed but test failed")
    else:
        print("\n  ❌ Some OCR dependencies are missing")
        print("\n  Install missing components and run this script again.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
