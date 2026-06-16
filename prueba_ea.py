import win32com.client
import sys

def test_ea_connection():
    try:
        print("Intentando conectar con Enterprise Architect vía COM...")
        # Despachar la aplicación de EA
        ea_app = win32com.client.Dispatch("EA.App")
        
        # Intentar obtener la versión de EA
        version = ea_app.Repository.LibraryVersion
        print(f"¡Éxito! Conexión establecida con EA. Versión de la librería: {version}")
        
        # Cerrar el proceso si es posible
        ea_app.Repository.Exit()
        print("Proceso EA.exe cerrado correctamente.")
        
    except Exception as e:
        print(f"Error al conectar con Enterprise Architect: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_ea_connection()
