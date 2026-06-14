import win32com.client
import sys
import os

def test_ea_connection():
    ea_app = None
    try:
        print("Iniciando Enterprise Architect...")
        ea_app = win32com.client.Dispatch("EA.App")
        
        filepath = r"D:\Proyecto_grado\diagrams_mvp\TestModel.eapx"
        if os.path.exists(filepath):
            os.remove(filepath)
            
        print(f"Creando nuevo archivo en {filepath}...")
        # EA Project interface usually has methods to create models
        # But Repository also has CreateModel. Let's try ProjectInterface if CreateModel fails
        # Actually, EA has a project interface: ea_app.Project
        # But Repository.CreateModel exists.
        project_interface = ea_app.Repository.GetProjectInterface()
        
        # Another way to create an EAP is copying the EABase file if we know it.
        # But let's try the built-in CreateModel? No, let's just use openfile, wait, openfile needs a file.
        # Let's try just opening a blank file? No, it's an Access DB.
        
        # To be safe, EA requires a valid file. If we can't create one programmatically, 
        # we can prompt the user to manually create an empty project in EA and save it as "base_model.eapx"
        pass
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if ea_app:
            ea_app.Repository.Exit()

if __name__ == "__main__":
    test_ea_connection()
