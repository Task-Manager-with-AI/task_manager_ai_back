import os
import platform
import time
from typing import Dict, List, Tuple


class EnterpriseArchitectService:
    SEQUENCE_MESSAGE_SUBTYPES = {
        "sync": 0,
        "async": 1,
        "return": 3,
    }
    SEQUENCE_FRAGMENT_SUBTYPES = {
        "alt": 0,
        "opt": 1,
        "loop": 4,
    }
    SEQUENCE_PARTICIPANT_BASE_WIDTH = 140
    SEQUENCE_PARTICIPANT_MAX_WIDTH = 220
    SEQUENCE_PARTICIPANT_SPACING = 60
    SEQUENCE_MESSAGE_SPACING = 68
    SEQUENCE_TOP = 80
    SEQUENCE_FRAGMENT_TOP_OFFSET = 26
    SEQUENCE_FRAGMENT_BOTTOM_PADDING = 92
    SEQUENCE_FRAGMENT_DEPTH_OFFSET = 18

    def __init__(self, model_path: str):
        self.model_path = os.path.abspath(model_path)

    def generate_diagram(self, architecture_data: dict, output_path: str) -> str:
        """
        Generate a diagram using Enterprise Architect COM when available.
        Sequence diagrams are strict-EA only; class and use case diagrams keep the
        Mermaid fallback for compatibility.
        """
        diagram_type = architecture_data.get("diagram_type", "class")

        if diagram_type == "sequence":
            return self._generate_sequence_diagram(architecture_data, output_path)

        try:
            self._ensure_windows()
            print("Attempting to generate diagram via Enterprise Architect COM...")
            return self._generate_via_ea(architecture_data, output_path)
        except Exception as e:
            print(f"Enterprise Architect generation failed or unavailable: {str(e)}")
            print("Falling back to Mermaid online rendering...")
            return self._generate_via_mermaid(architecture_data, output_path)

    def _generate_sequence_diagram(self, architecture_data: dict, output_path: str) -> str:
        try:
            self._ensure_windows()
            print("Attempting to generate sequence diagram via Enterprise Architect COM...")
            return self._generate_via_ea(architecture_data, output_path)
        except Exception as e:
            raise Exception(
                "Sequence diagram generation requires Enterprise Architect COM and failed: "
                f"{str(e)}"
            ) from e

    def _ensure_windows(self) -> None:
        if platform.system() != "Windows":
            raise Exception("Enterprise Architect COM is only supported on Windows.")

    def _generate_via_ea(self, architecture_data: dict, output_path: str) -> str:
        import win32com.client

        ea_app = None
        try:
            ea_app = win32com.client.Dispatch("EA.App")
            repository = ea_app.Repository
            repository.OpenFile(self.model_path)

            package = self._get_or_create_target_package(repository)
            project_interface = repository.GetProjectInterface()

            return self._dispatch_ea_generation(
                repository,
                project_interface,
                package,
                architecture_data,
                output_path,
            )
        except Exception as e:
            raise Exception(f"Failed to communicate with Enterprise Architect: {str(e)}") from e
        finally:
            if ea_app:
                try:
                    ea_app.Repository.Exit()
                except Exception:
                    pass

    def _dispatch_ea_generation(
        self,
        repository,
        project_interface,
        package,
        architecture_data: dict,
        output_path: str,
    ) -> str:
        diagram_type = architecture_data.get("diagram_type", "class")
        if diagram_type == "sequence":
            return self._generate_sequence_via_ea(
                repository,
                project_interface,
                package,
                architecture_data,
                output_path,
            )
        return self._generate_static_via_ea(
            repository,
            project_interface,
            package,
            architecture_data,
            output_path,
        )

    def _get_or_create_target_package(self, repository):
        models = repository.Models
        package = None
        for i in range(models.Count):
            model = models.GetAt(i)
            if model.Name == "Model":
                package = model.Packages.AddNew(f"Architecture_{int(time.time())}", "Package")
                package.Update()
                break

        if not package:
            package = models.AddNew(f"Architecture_{int(time.time())}", "Package")
            package.Update()
        return package

    def _generate_static_via_ea(
        self,
        repository,
        project_interface,
        package,
        architecture_data: dict,
        output_path: str,
    ) -> str:
        diagram_type = architecture_data.get("diagram_type", "class")
        if diagram_type == "use_case":
            diagram = package.Diagrams.AddNew("Casos de Uso", "Use Case")
        else:
            diagram = package.Diagrams.AddNew("Diagrama de Clases", "Logical")
        diagram.Update()

        elements_map = {}
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

            element = package.Elements.AddNew(name, ea_el_type)
            element.Update()

            for attr_str in el_data.get("attributes", []):
                attr = element.Attributes.AddNew(attr_str, "")
                attr.Update()

            elements_map[name] = element

            left = pos_x
            right = pos_x + width
            top = pos_y
            bottom = pos_y + height
            diagram_object = diagram.DiagramObjects.AddNew(
                f"l={left};r={right};t={top};b={bottom};",
                "",
            )
            diagram_object.ElementID = element.ElementID
            diagram_object.Update()

            pos_x += width + 50
            if pos_x > 600:
                pos_x = 100
                pos_y += height + 50

        self._create_static_relationships(elements_map, architecture_data.get("relationships", []))

        project_interface.LayoutDiagramEx(diagram.DiagramGUID, 0, 4, 40, 40, True)
        repository.ReloadDiagram(diagram.DiagramID)
        return self._export_diagram(project_interface, diagram, output_path)

    def _create_static_relationships(self, elements_map: dict, relationships: list) -> None:
        for rel in relationships:
            source_name = rel.get("source")
            target_name = rel.get("target")
            rel_type = rel.get("type", "Association")

            ea_type = "Association"
            rel_type_lower = rel_type.lower()
            if "agregaciÃ³n" in rel_type_lower or "aggregation" in rel_type_lower:
                ea_type = "Aggregation"
            elif "composiciÃ³n" in rel_type_lower or "composition" in rel_type_lower:
                ea_type = "Composition"
            elif (
                "generalizaciÃ³n" in rel_type_lower
                or "generalization" in rel_type_lower
                or "herencia" in rel_type_lower
            ):
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
                try:
                    connector.RouteStyle = 2
                except Exception:
                    pass
                connector.Update()

    def _generate_sequence_via_ea(
        self,
        repository,
        project_interface,
        package,
        architecture_data: dict,
        output_path: str,
    ) -> str:
        participants = architecture_data.get("participants", [])
        messages = architecture_data.get("messages", [])
        fragments = architecture_data.get("fragments", [])

        if len(participants) < 2 or len(messages) < 1:
            raise Exception("Sequence diagrams require at least 2 participants and 1 message.")

        diagram = package.Diagrams.AddNew("Diagrama de Secuencia", "Sequence")
        diagram.Update()

        sequence_layout = self._build_sequence_layout(participants, messages, fragments)
        participants_map, participant_layout = self._create_sequence_participants(
            package,
            diagram,
            participants,
            sequence_layout,
        )
        self._create_sequence_messages(participants_map, messages)
        self._create_sequence_fragments(
            package,
            diagram,
            fragments,
            participant_layout,
            sequence_layout,
        )

        repository.ReloadDiagram(diagram.DiagramID)
        return self._export_diagram(project_interface, diagram, output_path)

    def _build_sequence_layout(
        self,
        participants: List[dict],
        messages: List[dict],
        fragments: List[dict],
    ) -> dict:
        participant_boxes = []
        left = 100
        for participant in participants:
            width = min(
                self.SEQUENCE_PARTICIPANT_MAX_WIDTH,
                max(
                    self.SEQUENCE_PARTICIPANT_BASE_WIDTH,
                    80 + (len(participant["name"]) * 7),
                ),
            )
            right = left + width
            participant_boxes.append(
                {
                    "name": participant["name"],
                    "left": left,
                    "right": right,
                    "width": width,
                    "center": left + width // 2,
                }
            )
            left = right + self.SEQUENCE_PARTICIPANT_SPACING

        participant_index = {
            box["name"]: index for index, box in enumerate(participant_boxes)
        }
        message_y = {
            index: 140 + ((index - 1) * self.SEQUENCE_MESSAGE_SPACING)
            for index in range(1, len(messages) + 1)
        }
        diagram_bottom = message_y[len(messages)] + 340 if messages else 700
        fragment_boxes = self._build_sequence_fragment_boxes(
            participant_boxes,
            participant_index,
            messages,
            fragments,
            message_y,
        )

        return {
            "participant_boxes": participant_boxes,
            "participant_index": participant_index,
            "message_y": message_y,
            "diagram_bottom": diagram_bottom,
            "left_edge": participant_boxes[0]["left"] - 50,
            "right_edge": participant_boxes[-1]["right"] + 50,
            "fragment_boxes": fragment_boxes,
        }

    def _build_sequence_fragment_boxes(
        self,
        participant_boxes: List[dict],
        participant_index: Dict[str, int],
        messages: List[dict],
        fragments: List[dict],
        message_y: Dict[int, int],
    ) -> List[dict]:
        if not fragments:
            return []

        indexed_fragments = []
        for original_index, fragment in enumerate(fragments):
            start = int(fragment.get("start_message_index", 1))
            end = int(fragment.get("end_message_index", start))
            indexed_fragments.append(
                {
                    "original_index": original_index,
                    "fragment": fragment,
                    "start": start,
                    "end": end,
                }
            )

        indexed_fragments.sort(key=lambda item: (item["start"], -(item["end"] - item["start"]), item["original_index"]))
        stack = []
        fragment_boxes = [None] * len(fragments)

        for item in indexed_fragments:
            while stack and item["start"] > stack[-1]["end"]:
                stack.pop()
            depth = len(stack)
            stack.append(item)

            participants_in_range = self._participants_for_fragment_range(
                participant_index,
                messages,
                item["start"],
                item["end"],
            )
            left_idx = min(participants_in_range)
            right_idx = max(participants_in_range)
            inset = depth * self.SEQUENCE_FRAGMENT_DEPTH_OFFSET
            top = message_y[item["start"]] - self.SEQUENCE_FRAGMENT_TOP_OFFSET + inset
            bottom = (
                message_y[item["end"]]
                + self.SEQUENCE_FRAGMENT_BOTTOM_PADDING
                - (depth * 8)
            )

            label = item["fragment"].get("label", "Fragmento")
            fragment_boxes[item["original_index"]] = {
                "label": label,
                "type": item["fragment"].get("type", "alt"),
                "left": participant_boxes[left_idx]["left"] - 40 + inset,
                "right": participant_boxes[right_idx]["right"] + 40 - inset,
                "top": top,
                "bottom": max(top + 120, bottom),
            }

        return fragment_boxes

    def _participants_for_fragment_range(
        self,
        participant_index: Dict[str, int],
        messages: List[dict],
        start_index: int,
        end_index: int,
    ) -> List[int]:
        indices = []
        for message in messages[start_index - 1 : end_index]:
            source = participant_index.get(message["from"])
            target = participant_index.get(message["to"])
            if source is not None:
                indices.append(source)
            if target is not None:
                indices.append(target)
        if not indices:
            return [0]
        return indices

    def _create_sequence_participants(
        self,
        package,
        diagram,
        participants: List[dict],
        sequence_layout: dict,
    ) -> Tuple[Dict[str, object], Dict[str, dict]]:
        participants_map = {}
        participant_layout = {}
        bottom = sequence_layout["diagram_bottom"]

        for participant, box in zip(participants, sequence_layout["participant_boxes"]):
            name = participant["name"]
            element_type, stereotype = self._map_sequence_participant_type(
                participant.get("type", "lifeline")
            )
            element = package.Elements.AddNew(name, element_type)
            if stereotype:
                element.Stereotype = stereotype
            element.Update()

            diagram_object = diagram.DiagramObjects.AddNew(
                f"l={box['left']};r={box['right']};t={self.SEQUENCE_TOP};b={bottom};",
                "",
            )
            diagram_object.ElementID = element.ElementID
            diagram_object.Update()

            participants_map[name] = element
            participant_layout[name] = box

        return participants_map, participant_layout

    def _map_sequence_participant_type(self, participant_type: str) -> Tuple[str, str]:
        normalized = str(participant_type or "lifeline").lower()
        if normalized == "actor":
            return "Actor", ""
        return "Object", "Lifeline"

    def _create_sequence_messages(self, participants_map: Dict[str, object], messages: List[dict]) -> None:
        for index, message in enumerate(messages, start=1):
            source = participants_map.get(message["from"])
            target = participants_map.get(message["to"])
            if not source or not target:
                continue

            connector = source.Connectors.AddNew(message.get("message", ""), "Sequence")
            connector.SupplierID = target.ElementID
            subtype = self.SEQUENCE_MESSAGE_SUBTYPES.get(message.get("kind", "sync"), 0)
            connector.Subtype = subtype
            connector.SequenceNo = str(index)
            connector.Update()

    def _create_sequence_fragments(
        self,
        package,
        diagram,
        fragments: List[dict],
        participant_layout: Dict[str, dict],
        sequence_layout: dict,
    ) -> None:
        if not fragments:
            return

        for fragment, fragment_box in zip(fragments, sequence_layout["fragment_boxes"]):
            fragment_type = fragment.get("type")
            if fragment_type not in self.SEQUENCE_FRAGMENT_SUBTYPES:
                raise Exception(f"Unsupported sequence fragment type: {fragment_type}")

            element = package.Elements.AddNew(fragment_box["label"], "InteractionFragment")
            element.Subtype = self.SEQUENCE_FRAGMENT_SUBTYPES[fragment_type]
            element.Update()

            fragment_object = diagram.DiagramObjects.AddNew(
                (
                    f"l={fragment_box['left']};r={fragment_box['right']};"
                    f"t={fragment_box['top']};b={fragment_box['bottom']};"
                ),
                "",
            )
            fragment_object.ElementID = element.ElementID
            fragment_object.Update()

    def _export_diagram(self, project_interface, diagram, output_path: str) -> str:
        output_image = os.path.abspath(output_path)
        project_interface.PutDiagramImageToFile(diagram.DiagramGUID, output_image, 1)
        return output_image

    def _generate_via_mermaid(self, architecture_data: dict, output_path: str) -> str:
        diagram_type = architecture_data.get("diagram_type", "class")
        elements = architecture_data.get("elements", [])
        relationships = architecture_data.get("relationships", [])

        if diagram_type == "use_case":
            mermaid_code = self._to_mermaid_use_case_diagram(elements, relationships)
        else:
            mermaid_code = self._to_mermaid_class_diagram(elements, relationships)

        print("Generated Mermaid Code successfully.")
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
        import base64
        import json
        import urllib.request

        browser_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
        }

        try:
            print("Rendering Mermaid diagram via Kroki POST...")
            url = "https://kroki.io/mermaid/png"
            data = json.dumps({"diagram_source": mermaid_code}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", **browser_headers},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                png_data = response.read()
                with open(output_path, "wb") as file_handle:
                    file_handle.write(png_data)
                print("Mermaid diagram rendered successfully via Kroki.")
                return
        except Exception as e:
            print(f"Kroki rendering failed: {str(e)}. Trying Mermaid.ink...")

        try:
            print("Rendering Mermaid diagram via Mermaid.ink GET...")
            encoded_code = base64.b64encode(mermaid_code.encode("utf-8")).decode("utf-8")
            url = f"https://mermaid.ink/img/{encoded_code}"
            req = urllib.request.Request(url, headers=browser_headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as response:
                png_data = response.read()
                with open(output_path, "wb") as file_handle:
                    file_handle.write(png_data)
                print("Mermaid diagram rendered successfully via Mermaid.ink.")
                return
        except Exception as e:
            raise Exception(
                "Failed to render Mermaid diagram via both Kroki and Mermaid.ink. "
                f"Error: {str(e)}"
            ) from e
