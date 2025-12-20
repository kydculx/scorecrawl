import sys
import subprocess
import os

def check_and_install_packages():
    """필요한 패키지가 설치되어 있는지 확인하고 없으면 설치"""
    required_packages = {
        'pandas': 'pandas',
        'PyQt5': 'PyQt5',
        'playwright': 'playwright',
        'openpyxl': 'openpyxl',
        'lxml': 'lxml'  # read_html을 위해 필요
    }
    
    missing_packages = []
    
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("필요한 패키지가 설치되지 않았습니다. 자동으로 설치합니다...")
        print(f"설치할 패키지: {', '.join(missing_packages)}")
        
        # 프로젝트 루트 디렉토리 찾기 (utils 상위)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        requirements_file = os.path.join(project_root, 'requirements.txt')
        
        if os.path.exists(requirements_file):
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file])
                print("패키지 설치가 완료되었습니다.")
            except subprocess.CalledProcessError:
                print("패키지 설치 중 오류가 발생했습니다. 수동으로 설치해주세요:")
                print(f"pip install -r requirements.txt")
                sys.exit(1)
        else:
            try:
                for package in missing_packages:
                    print(f"{package} 설치 중...")
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print("패키지 설치가 완료되었습니다.")
            except subprocess.CalledProcessError:
                print("패키지 설치 중 오류가 발생했습니다. 수동으로 설치해주세요:")
                print(f"pip install {' '.join(missing_packages)}")
                sys.exit(1)
        
        # playwright의 경우 브라우저도 설치 필요
        try:
            import playwright
            print("Playwright 브라우저 설치 중...")
            subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
        except:
            pass
