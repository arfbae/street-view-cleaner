import importlib

MODULES=["backend.app.config","backend.app.providers.base","backend.app.providers.factory","backend.app.providers.router","backend.app.main"]

def verify_project_structure():
    for name in MODULES:
        importlib.import_module(name)
        print(f"SUCCESS: {name}")
    print("SUCCESS: no circular import errors detected")
    return True

if __name__ == "__main__": verify_project_structure()
