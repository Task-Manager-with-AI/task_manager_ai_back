import os
import time
import platform

class EnterpriseArchitectService:
    def __init__(self, model_path: str):
        self.model_path = os.path.abspath(model_path)
    
    def generate_diagram(self, architecture_data: dict, output_path: str) -> str:
        """
        Generates a diagram. It tries to use Enterprise Architect COM interface first.
        If it fails, or if not running on Windows, it falls back to generating
        a Mermaid diagram and rendering it to a PNG via public APIs (Kroki/Mermaid.ink).
        """
        # Try Enterprise Architect COM automation
        try:
            if platform.system() != "Windows":
                raise Exception("Enterprise Architect COM is only supported on Windows.")
            
            print("Attempting to generate diagram via Enterprise Architect COM...")
            return self._generate_via_ea(architecture_data, output_path)
        except Exception as e:
            print(f"Enterprise Architect generation failed or unavailable: {str(e)}")
            print("Falling back to Mermaid online rendering...")
            return self._generate_via_mermaid(architecture_data, output_path)

    def _generate_via_ea(self, architecture_data: dict, output_path: str) -> str:
        # Import win32com dynamically so it doesn't fail on non-Windows systems at import time
        import win32com.client

        ea_app = None
        try:
            ea_app = win32com.client.Dispatch("EA.App")
            repository = ea_app.Repository
            
            # Open the base model
            repository.OpenFile(self.model_path)
            
            models = repository.Models
            package = None
            for i in range(models.Count):
                model = models.GetAt(i)
                if model.Name == "Model":
                    package = model.Packages.AddNew("Architecture_" + str(int(time.time())), "Package")
                    package.Update()
                    break
            
            if not package:
                package = models.AddNew("Architecture_" + str(int(time.time())), "Package")
                package.Update()
                
            diagram_type = architecture_data.get("diagram_type", "class")
            
            # Create a diagram
            if diagram_type == "use_case":
                diagram = package.Diagrams.AddNew("Casos de Uso", "Use Case")
            else:
                diagram = package.Diagrams.AddNew("Diagrama de Clases", "Logical")
            diagram.Update()
            
            elements_map = {}
            
            # Positioning variables
            pos_x = 100
            pos_y = 100
            width = 150
            height = 120
            
            elements_data = architecture_data.get("elements", architecture_data.get("classes", []))
            for el_data in elements_data:
                name = el_data.get("name", "Unnamed")
                el_type = el_data.get("type", "Class")
                
                if el_type.lower() == "usecase":
                    ea_el_type = "UseCase"
                elif el_type.lower() == "actor":
                    ea_el_type = "Actor"
                else:
                    ea_el_type = "Class"
                    
                # Create element
                element = package.Elements.AddNew(name, ea_el_type)
                element.Update()
                
                # Add attributes
                attributes = el_data.get("attributes", [])
                for attr_str in attributes:
                    attr = element.Attributes.AddNew(attr_str, "")
                    attr.Update()
                    
                elements_map[name] = element
                
                # Add element to diagram
                l = pos_x
                r = pos_x + width
                t = pos_y
                b = pos_y + height
                diagram_object = diagram.DiagramObjects.AddNew(f"l={l};r={r};t={t};b={b};", "")
                diagram_object.ElementID = element.ElementID
                diagram_object.Update()
                
                # Update pos for next class (wrap around after 3)
                pos_x += width + 50
                if pos_x > 600:
                    pos_x = 100
                    pos_y += height + 50

            # Relationships
            relationships = architecture_data.get("relationships", [])
            for rel in relationships:
                source_name = rel.get("source")
                target_name = rel.get("target")
                rel_type = rel.get("type", "Association")
                
                # Map some Spanish names to EA types
                ea_type = "Association"
                rel_type_lower = rel_type.lower()
                if "agregación" in rel_type_lower or "aggregation" in rel_type_lower:
                    ea_type = "Aggregation"
                elif "composición" in rel_type_lower or "composition" in rel_type_lower:
                    ea_type = "Composition"
                elif "generalización" in rel_type_lower or "generalization" in rel_type_lower or "herencia" in rel_type_lower:
                    ea_type = "Generalization"
                    
                source_el = elements_map.get(source_name)
                target_el = elements_map.get(target_name)
                
                if source_el and target_el:
                    if "include" in rel_type_lower or "extend" in rel_type_lower:
                        connector = source_el.Connectors.AddNew("", "Dependency")
                        connector.Stereotype = "include" if "include" in rel_type_lower else "extend"
                    else:
                        connector = source_el.Connectors.AddNew("", ea_type)
                        
                    connector.SupplierID = target_el.ElementID
                    # Try to set orthogonal routing style if available
                    try:
                        connector.RouteStyle = 2
                    except Exception:
                        pass
                    connector.Update()
            
            # Use EA's built-in Layout to arrange elements automatically and prevent overlaps
            project_interface = repository.GetProjectInterface()
            project_interface.LayoutDiagramEx(diagram.DiagramGUID, 0, 4, 40, 40, True)
            
            # Refresh to show connectors
            repository.ReloadDiagram(diagram.DiagramID)
            
            # Export the diagram to an image
            output_image = os.path.abspath(output_path)
            project_interface.PutDiagramImageToFile(diagram.DiagramGUID, output_image, 1)
            
            return output_image
            
        except Exception as e:
            raise Exception(f"Failed to communicate with Enterprise Architect: {str(e)}")
        finally:
            if ea_app:
                try:
                    ea_app.Repository.Exit()
                except Exception:
                    pass

    def _generate_via_mermaid(self, architecture_data: dict, output_path: str) -> str:
        diagram_type = architecture_data.get("diagram_type", "class")
        elements = architecture_data.get("elements", [])
        relationships = architecture_data.get("relationships", [])

        if diagram_type == "use_case":
            mermaid_code = self._to_mermaid_use_case_diagram(elements, relationships)
        else:
            mermaid_code = self._to_mermaid_class_diagram(elements, relationships)

        # Print using ascii safe text to prevent Windows cp1252 console encoding errors
        print("Generated Mermaid Code successfully.")
        
        # Render code to PNG and write to output_path
        self._render_mermaid_to_png(mermaid_code, output_path)
        
        return os.path.abspath(output_path)

    def _to_mermaid_class_diagram(self, elements: list, relationships: list) -> str:
        lines = ["classDiagram"]
        for el in elements:
            name = el.get("name", "").replace(" ", "_").replace("-", "_")
            if not name:
                continue
            el_type = el.get("type", "Class")
            if el_type.lower() != "class":
                continue
            
            lines.append(f"  class {name} {{")
            for attr in el.get("attributes", []):
                cleaned_attr = attr.replace("{", "").replace("}", "").replace(";", "")
                lines.append(f"    {cleaned_attr}")
            lines.append("  }")
        
        for rel in relationships:
            src = rel.get("source", "").replace(" ", "_").replace("-", "_")
            tgt = rel.get("target", "").replace(" ", "_").replace("-", "_")
            if not src or not tgt:
                continue
            r_type = rel.get("type", "Association").lower()
            
            # Determine arrow style
            arrow = "-->"
            if "general" in r_type or "herencia" in r_type or "subclass" in r_type:
                arrow = "--|>"
            elif "comp" in r_type:
                arrow = "--*"
            elif "agreg" in r_type:
                arrow = "--o"
            
            lines.append(f"  {src} {arrow} {tgt}")
        return "\n".join(lines)

    def _to_mermaid_use_case_diagram(self, elements: list, relationships: list) -> str:
        lines = ["graph LR"]
        for el in elements:
            name = el.get("name", "")
            if not name:
                continue
            safe_id = name.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").replace('"', "")
            el_type = el.get("type", "UseCase")
            if el_type.lower() == "actor":
                lines.append(f'  {safe_id}["Actor: {name}"]')
            else:
                lines.append(f'  {safe_id}(["{name}"])')
        
        for rel in relationships:
            src = rel.get("source", "").replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").replace('"', "")
            tgt = rel.get("target", "").replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").replace('"', "")
            if not src or not tgt:
                continue
            
            r_type = rel.get("type", "").lower()
            if "include" in r_type:
                lines.append(f'  {src} -.->|"<<include>>"| {tgt}')
            elif "extend" in r_type:
                lines.append(f'  {src} -.->|"<<extend>>"| {tgt}')
            else:
                lines.append(f"  {src} --- {tgt}")
        return "\n".join(lines)

    def _render_mermaid_to_png(self, mermaid_code: str, output_path: str) -> None:
        import urllib.request
        import json
        import base64

        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Try Kroki first
        try:
            print("Rendering Mermaid diagram via Kroki POST...")
            url = "https://kroki.io/mermaid/png"
            data = json.dumps({"diagram_source": mermaid_code}).encode("utf-8")
            
            req_headers = {
                "Content-Type": "application/json",
                **browser_headers
            }
            
            req = urllib.request.Request(
                url, 
                data=data, 
                headers=req_headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                png_data = response.read()
                with open(output_path, "wb") as f:
                    f.write(png_data)
                print("Mermaid diagram rendered successfully via Kroki.")
                return
        except Exception as e:
            print(f"Kroki rendering failed: {str(e)}. Trying Mermaid.ink...")

        # Fallback to Mermaid.ink
        try:
            print("Rendering Mermaid diagram via Mermaid.ink GET...")
            encoded_code = base64.b64encode(mermaid_code.encode("utf-8")).decode("utf-8")
            url = f"https://mermaid.ink/img/{encoded_code}"
            
            req = urllib.request.Request(url, headers=browser_headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as response:
                png_data = response.read()
                with open(output_path, "wb") as f:
                    f.write(png_data)
                print("Mermaid diagram rendered successfully via Mermaid.ink.")
                return
        except Exception as e:
            raise Exception(f"Failed to render Mermaid diagram via both Kroki and Mermaid.ink. Error: {str(e)}")
