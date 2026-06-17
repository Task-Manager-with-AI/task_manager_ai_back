import os
import platform
import time
from typing import Dict, List, Optional, Set, Tuple


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
    SEQUENCE_ALT_TOP_OFFSET = 44
    SEQUENCE_ALT_BOTTOM_PADDING = 20
    ACTIVITY_CENTER_X = 420
    ACTIVITY_LEFT_X = 130
    ACTIVITY_LEFT_OUTER_X = 30
    ACTIVITY_RIGHT_X = 710
    ACTIVITY_RIGHT_OUTER_X = 810
    ACTIVITY_LANE_GAP = 260
    ACTIVITY_START_Y = 60
    ACTIVITY_MAIN_SPACING = 105
    ACTIVITY_BRANCH_SPACING = 112
    ACTIVITY_BRANCH_OFFSET = 44
    ACTIVITY_BRANCH_CLEARANCE = 36
    ACTIVITY_PARALLEL_OFFSET = 230
    ACTIVITY_ACTION_WIDTH = 250
    ACTIVITY_ACTION_HEIGHT = 55
    ACTIVITY_DECISION_WIDTH = 90
    ACTIVITY_DECISION_HEIGHT = 70
    ACTIVITY_NODE_SIZE = 40
    ACTIVITY_OBJECT_WIDTH = 180
    ACTIVITY_OBJECT_HEIGHT = 48
    ACTIVITY_SYNC_WIDTH = 180
    ACTIVITY_SYNC_HEIGHT = 18
    COMPONENT_DEFAULT_LAYER_ORDER = ("client", "gateway", "service", "support", "external", "data")
    COMPONENT_BASE_WIDTH = 250
    COMPONENT_MAX_WIDTH = 320
    COMPONENT_HEIGHT = 88
    COMPONENT_Y_START = 60
    COMPONENT_Y_SPACING = 122
    COMPONENT_LAYER_GAP = 90
    COMPONENT_CHAR_WIDTH = 7
    DEPLOYMENT_NODE_ORDER = ("external_node", "device", "node", "execution_environment", "database_node")
    DEPLOYMENT_NODE_BASE_WIDTH = 240
    DEPLOYMENT_NODE_HEIGHT = 150
    DEPLOYMENT_NODE_X_START = 40
    DEPLOYMENT_NODE_Y_START = 60
    DEPLOYMENT_NODE_GAP = 120
    DEPLOYMENT_LOWER_ROW_Y = 500
    DEPLOYMENT_ARTIFACT_WIDTH = 180
    DEPLOYMENT_ARTIFACT_HEIGHT = 48
    DEPLOYMENT_ARTIFACT_SPACING = 18
    DEPLOYMENT_NODE_INSET_X = 28
    DEPLOYMENT_NODE_INSET_TOP = 54
    DEPLOYMENT_NODE_INSET_BOTTOM = 24
    DEPLOYMENT_SEQUENCE_NODE = 10
    DEPLOYMENT_SEQUENCE_ARTIFACT = 1

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
        if diagram_type == "activity":
            return self._generate_activity_diagram(architecture_data, output_path)
        if diagram_type == "component":
            return self._generate_component_diagram(architecture_data, output_path)
        if diagram_type == "deployment":
            return self._generate_deployment_diagram(architecture_data, output_path)

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

    def _generate_activity_diagram(self, architecture_data: dict, output_path: str) -> str:
        try:
            self._ensure_windows()
            print("Attempting to generate activity diagram via Enterprise Architect COM...")
            return self._generate_via_ea(architecture_data, output_path)
        except Exception as e:
            raise Exception(
                "Activity diagram generation requires Enterprise Architect COM and failed: "
                f"{str(e)}"
            ) from e

    def _generate_component_diagram(self, architecture_data: dict, output_path: str) -> str:
        try:
            self._ensure_windows()
            print("Attempting to generate component diagram via Enterprise Architect COM...")
            return self._generate_via_ea(architecture_data, output_path)
        except Exception as e:
            raise Exception(
                "Component diagram generation requires Enterprise Architect COM and failed: "
                f"{str(e)}"
            ) from e

    def _generate_deployment_diagram(self, architecture_data: dict, output_path: str) -> str:
        try:
            self._ensure_windows()
            print("Attempting to generate deployment diagram via Enterprise Architect COM...")
            return self._generate_via_ea(architecture_data, output_path)
        except Exception as e:
            raise Exception(
                "Deployment diagram generation requires Enterprise Architect COM and failed: "
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
        if diagram_type == "activity":
            return self._generate_activity_via_ea(
                repository,
                project_interface,
                package,
                architecture_data,
                output_path,
            )
        if diagram_type == "component":
            return self._generate_component_via_ea(
                repository,
                project_interface,
                package,
                architecture_data,
                output_path,
            )
        if diagram_type == "deployment":
            return self._generate_deployment_via_ea(
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
        activations = architecture_data.get("activations", [])

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
        self._create_sequence_messages(diagram, participants_map, participants, messages, activations)
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
                item["fragment"],
            )
            left_idx = min(participants_in_range)
            right_idx = max(participants_in_range)
            inset = depth * self.SEQUENCE_FRAGMENT_DEPTH_OFFSET
            fragment_type = item["fragment"].get("type", "alt")
            top_offset = (
                self.SEQUENCE_ALT_TOP_OFFSET
                if fragment_type == "alt"
                else self.SEQUENCE_FRAGMENT_TOP_OFFSET
            )
            bottom_padding = (
                self.SEQUENCE_ALT_BOTTOM_PADDING
                if fragment_type == "alt"
                else self.SEQUENCE_FRAGMENT_BOTTOM_PADDING
            )
            top = message_y[item["start"]] - top_offset + inset
            bottom = (
                message_y[item["end"]]
                + bottom_padding
                - (depth * 8)
            )

            label = self._format_sequence_fragment_label(item["fragment"])
            fragment_boxes[item["original_index"]] = {
                "label": label,
                "type": fragment_type,
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
        fragment: dict | None = None,
    ) -> List[int]:
        if fragment and str(fragment.get("type", "")).lower() == "alt":
            branch_indices = self._participants_for_alt_branches(
                participant_index,
                messages,
                fragment.get("branches") or [],
            )
            if branch_indices:
                return branch_indices

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

    def _participants_for_alt_branches(
        self,
        participant_index: Dict[str, int],
        messages: List[dict],
        branches: List[dict],
    ) -> List[int]:
        if not branches:
            return []

        indices = []
        for branch in branches:
            start = int(branch.get("start_message_index", 1))
            end = int(branch.get("end_message_index", start))
            for message in messages[max(0, start - 1) : max(0, end)]:
                source_name = message.get("from")
                target_name = message.get("to")
                source = participant_index.get(source_name)
                target = participant_index.get(target_name)

                if source is not None:
                    indices.append(source)
                if target is not None:
                    indices.append(target)

        filtered = self._filter_auxiliary_alt_participants(indices, participant_index, messages, branches)
        return filtered or indices

    def _filter_auxiliary_alt_participants(
        self,
        indices: List[int],
        participant_index: Dict[str, int],
        messages: List[dict],
        branches: List[dict],
    ) -> List[int]:
        if not indices:
            return []

        unique_indices = sorted(set(indices))
        branch_message_counts = {index: 0 for index in unique_indices}
        terminal_target_only = {index: True for index in unique_indices}
        branch_starts = {
            int(branch.get("start_message_index", 1))
            for branch in branches
            if branch.get("start_message_index")
        }

        for branch in branches:
            start = int(branch.get("start_message_index", 1))
            end = int(branch.get("end_message_index", start))
            for message_index, message in enumerate(messages[max(0, start - 1) : max(0, end)], start=start):
                source = participant_index.get(message.get("from"))
                target = participant_index.get(message.get("to"))
                if source is not None and source in branch_message_counts:
                    branch_message_counts[source] += 1
                    terminal_target_only[source] = False
                if target is not None and target in branch_message_counts:
                    branch_message_counts[target] += 1

                # Keep the participants that appear at the branch entry points.
                if message_index in branch_starts:
                    for participant in (source, target):
                        if participant is not None and participant in branch_message_counts:
                            branch_message_counts[participant] += 2
                            terminal_target_only[participant] = False

                if source is not None and source in terminal_target_only:
                    terminal_target_only[source] = False

        # Prefer participants with repeated involvement across branch messages.
        strong_participants = [
            participant
            for participant, score in branch_message_counts.items()
            if score >= 2 and not terminal_target_only[participant]
        ]
        if len(strong_participants) >= 2:
            return sorted(strong_participants)

        non_terminal = [
            participant
            for participant in unique_indices
            if not terminal_target_only[participant]
        ]
        if len(non_terminal) >= 2:
            return non_terminal

        return sorted(strong_participants or non_terminal)

    def _format_sequence_fragment_label(self, fragment: dict) -> str:
        fragment_type = str(fragment.get("type", "alt") or "alt").lower()
        if fragment_type != "alt":
            return fragment.get("label", "Fragmento")

        branches = fragment.get("branches") or []
        if len(branches) > 1:
            return "alt"

        guard = str(fragment.get("guard") or "").strip()
        label = str(fragment.get("label") or "").strip()
        if guard:
            return guard
        return label or "alt"

    def _sequence_fragment_element_name(self, fragment: dict) -> str:
        fragment_type = str(fragment.get("type", "alt") or "alt").lower()
        if fragment_type == "alt":
            return "alt"
        return self._format_sequence_fragment_label(fragment)

    def _build_sequence_fragment_notes(self, fragment: dict) -> str:
        branches = fragment.get("branches") or []
        if branches:
            labels = []
            for branch in branches:
                branch_label = str(branch.get("guard") or branch.get("label") or "").strip()
                if branch_label:
                    labels.append(branch_label)
            if labels:
                return "\n\n".join(labels)

        return str(fragment.get("guard") or fragment.get("label") or "").strip()

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

    def _create_sequence_messages(
        self,
        diagram,
        participants_map: Dict[str, object],
        participants: List[dict],
        messages: List[dict],
        activations: List[dict],
    ) -> None:
        participant_types = {
            participant["name"]: str(participant.get("type", "lifeline") or "lifeline").lower()
            for participant in participants
        }
        activation_plan = self._build_sequence_activation_plan(
            participants,
            messages,
            activations,
        )

        for index, message in enumerate(messages, start=1):
            source = participants_map.get(message["from"])
            target = participants_map.get(message["to"])
            if not source or not target:
                continue

            connector = source.Connectors.AddNew(message.get("message", ""), "Sequence")
            connector.ClientID = source.ElementID
            connector.SupplierID = target.ElementID
            connector.Direction = "Source -> Destination"
            subtype = self.SEQUENCE_MESSAGE_SUBTYPES.get(message.get("kind", "sync"), 0)
            connector.Subtype = subtype
            connector.SequenceNo = str(index)
            state_flags = self._build_sequence_message_state_flags(
                message_index=index,
                message=message,
                activation_plan=activation_plan,
                participant_types=participant_types,
            )
            if state_flags:
                connector.StateFlags = state_flags
            connector.Update()
            source.Connectors.Refresh()

            diagram_link = diagram.DiagramLinks.AddNew("", "")
            diagram_link.ConnectorID = connector.ConnectorID
            diagram_link.Update()

        diagram.DiagramLinks.Refresh()

    def _build_sequence_activation_plan(
        self,
        participants: List[dict],
        messages: List[dict],
        activations: List[dict],
    ) -> Dict[str, List[dict]]:
        plan: Dict[str, List[dict]] = {}

        for participant in participants:
            participant_name = participant["name"]
            participant_type = str(participant.get("type", "lifeline") or "lifeline").lower()
            if participant_type == "actor":
                continue

            explicit = [
                {
                    "start_message_index": int(activation["start_message_index"]),
                    "end_message_index": int(activation["end_message_index"]),
                    "source": "explicit",
                }
                for activation in activations
                if activation.get("participant") == participant_name
            ]

            if explicit:
                plan[participant_name] = explicit
                continue

            inferred = self._infer_sequence_participant_activations(
                participant_name,
                participant_type,
                messages,
            )
            if inferred:
                plan[participant_name] = inferred

        return plan

    def _infer_sequence_participant_activations(
        self,
        participant_name: str,
        participant_type: str,
        messages: List[dict],
    ) -> List[dict]:
        incoming_sync_indices = [
            index
            for index, message in enumerate(messages, start=1)
            if message.get("to") == participant_name and message.get("kind") in {"sync", "async"}
        ]
        if not incoming_sync_indices:
            return []

        activations = []
        for start_index in incoming_sync_indices:
            end_index = start_index
            for index in range(start_index, len(messages) + 1):
                current = messages[index - 1]
                if current.get("from") != participant_name and current.get("to") != participant_name:
                    continue
                end_index = index
                if current.get("from") == participant_name and current.get("kind") == "return":
                    break

            activations.append(
                {
                    "start_message_index": start_index,
                    "end_message_index": end_index,
                    "source": "inferred",
                    "participant_type": participant_type,
                }
            )

        # For passive entities such as databases, keep only the narrowest activation span.
        if participant_type == "entity":
            shortest = min(
                activations,
                key=lambda activation: (
                    activation["end_message_index"] - activation["start_message_index"],
                    activation["start_message_index"],
                ),
            )
            return [shortest]

        return activations

    def _build_sequence_message_state_flags(
        self,
        message_index: int,
        message: dict,
        activation_plan: Dict[str, List[dict]],
        participant_types: Dict[str, str],
    ) -> str:
        flags: List[str] = []

        target_name = message.get("to")
        source_name = message.get("from")
        target_type = participant_types.get(target_name, "lifeline")
        source_type = participant_types.get(source_name, "lifeline")

        if target_name and self._is_activation_start(activation_plan, target_name, message_index):
            flags.append("ForceActivation=1")

        if source_name and self._is_activation_end(activation_plan, source_name, message_index):
            flags.append("EndActivation=1")

        # Databases/entities tend to render floating activation bars when EA infers
        # a longer activation than intended. Tighten them to the single round-trip.
        if source_type == "entity" and message.get("kind") == "return":
            if "EndActivation=1" not in flags:
                flags.append("EndActivation=1")
            flags.append("StopActivation=1")

        if target_type == "entity" and message.get("kind") in {"sync", "async"}:
            if "ForceActivation=1" not in flags:
                flags.append("ForceActivation=1")

        return ";".join(dict.fromkeys(flags)) + (";" if flags else "")

    def _is_activation_start(
        self,
        activation_plan: Dict[str, List[dict]],
        participant_name: str,
        message_index: int,
    ) -> bool:
        return any(
            activation.get("start_message_index") == message_index
            for activation in activation_plan.get(participant_name, [])
        )

    def _is_activation_end(
        self,
        activation_plan: Dict[str, List[dict]],
        participant_name: str,
        message_index: int,
    ) -> bool:
        return any(
            activation.get("end_message_index") == message_index
            for activation in activation_plan.get(participant_name, [])
        )

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

            element = package.Elements.AddNew(
                self._sequence_fragment_element_name(fragment),
                "InteractionFragment",
            )
            element.Subtype = self.SEQUENCE_FRAGMENT_SUBTYPES[fragment_type]
            if fragment_type == "alt":
                element.Stereotype = "alt"
                element.Alias = "alt"
                element.Notes = self._build_sequence_fragment_notes(fragment)
            elif fragment_box["label"]:
                element.Notes = fragment_box["label"]
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

        diagram.DiagramObjects.Refresh()

    def _export_diagram(self, project_interface, diagram, output_path: str) -> str:
        output_image = os.path.abspath(output_path)
        project_interface.PutDiagramImageToFile(diagram.DiagramGUID, output_image, 1)
        return output_image

    def _generate_component_via_ea(
        self,
        repository,
        project_interface,
        package,
        architecture_data: dict,
        output_path: str,
    ) -> str:
        layers = architecture_data.get("layers", [])
        components = architecture_data.get("components", [])
        dependencies = architecture_data.get("dependencies", [])

        if len(components) < 2 or len(dependencies) < 1:
            raise Exception("Component diagrams require at least 2 components and 1 dependency.")

        diagram = package.Diagrams.AddNew("Diagrama de Componentes", "Component")
        diagram.Update()

        layout = self._build_component_layout(components, layers)
        elements_map = self._create_component_elements(package, diagram, components, layout)
        self._create_component_dependencies(diagram, elements_map, dependencies)

        diagram.Update()
        diagram.DiagramObjects.Refresh()
        diagram.DiagramLinks.Refresh()
        repository.ReloadDiagram(diagram.DiagramID)
        return self._export_diagram(project_interface, diagram, output_path)

    def _build_component_layout(
        self,
        components: List[dict],
        layers: List[str],
    ) -> Dict[str, Dict[str, int]]:
        ordered_layers = [layer for layer in self.COMPONENT_DEFAULT_LAYER_ORDER if layer in layers]
        ordered_layers.extend(layer for layer in layers if layer not in ordered_layers)

        components_by_layer: Dict[str, List[dict]] = {}
        layer_widths: Dict[str, int] = {}
        for component in components:
            layer = component.get("layer", "service")
            components_by_layer.setdefault(layer, []).append(component)
            width = self._component_box_width(component)
            layer_widths[layer] = max(layer_widths.get(layer, self.COMPONENT_BASE_WIDTH), width)

        layer_x: Dict[str, int] = {}
        cursor_x = 40
        for layer in ordered_layers:
            layer_x[layer] = cursor_x
            cursor_x += layer_widths.get(layer, self.COMPONENT_BASE_WIDTH) + self.COMPONENT_LAYER_GAP

        layout: Dict[str, Dict[str, int]] = {}
        layer_offsets: Dict[str, int] = {}

        for component in components:
            layer = component.get("layer", "service")
            current_index = layer_offsets.get(layer, 0)
            top_y = self.COMPONENT_Y_START + (current_index * self.COMPONENT_Y_SPACING)
            width = self._component_box_width(component)
            layout[component["id"]] = {
                "left": layer_x.get(layer, layer_x.get("service", 620)),
                "top": top_y,
                "width": width,
                "height": self.COMPONENT_HEIGHT,
            }
            layer_offsets[layer] = current_index + 1

        return layout

    def _component_box_width(self, component: dict) -> int:
        texts = [str(component.get("name", "")).strip()]
        interfaces = component.get("interfaces", {}) if isinstance(component.get("interfaces"), dict) else {}
        texts.extend(str(item).strip() for item in (interfaces.get("provided") or []) if str(item).strip())
        texts.extend(str(item).strip() for item in (interfaces.get("required") or []) if str(item).strip())
        longest = max((len(text) for text in texts if text), default=0)
        estimated = self.COMPONENT_BASE_WIDTH + max(0, longest - 18) * self.COMPONENT_CHAR_WIDTH
        return max(self.COMPONENT_BASE_WIDTH, min(estimated, self.COMPONENT_MAX_WIDTH))

    def _build_component_notes(self, component: dict) -> str:
        interfaces = component.get("interfaces", {}) if isinstance(component.get("interfaces"), dict) else {}
        provided = [item for item in (interfaces.get("provided") or []) if item]
        required = [item for item in (interfaces.get("required") or []) if item]
        lines: List[str] = []
        if provided:
            lines.append("Provided interfaces:")
            lines.extend(f"- {name}" for name in provided)
        if required:
            lines.append("Required interfaces:")
            lines.extend(f"- {name}" for name in required)
        return "\n".join(lines)

    def _create_component_elements(
        self,
        package,
        diagram,
        components: List[dict],
        layout: Dict[str, Dict[str, int]],
    ) -> Dict[str, object]:
        elements_map: Dict[str, object] = {}

        for component in components:
            element = package.Elements.AddNew(component["name"], "Component")
            stereotype = component.get("stereotype", "")
            if stereotype:
                element.Stereotype = stereotype
            notes = self._build_component_notes(component)
            if notes:
                element.Notes = notes
            element.Update()
            package.Elements.Refresh()

            box = layout[component["id"]]
            diagram_object = diagram.DiagramObjects.AddNew(
                (
                    f"l={box['left']};r={box['left'] + box['width']};"
                    f"t={box['top']};b={box['top'] + box['height']};"
                ),
                "",
            )
            diagram_object.ElementID = element.ElementID
            diagram_object.Update()

            elements_map[component["id"]] = element

        diagram.DiagramObjects.Refresh()
        return elements_map

    def _create_component_dependencies(
        self,
        diagram,
        elements_map: Dict[str, object],
        dependencies: List[dict],
    ) -> None:
        for dependency in dependencies:
            source_element = elements_map.get(dependency["from"])
            target_element = elements_map.get(dependency["to"])
            if not source_element or not target_element:
                continue

            connector = source_element.Connectors.AddNew(dependency.get("label", ""), "Dependency")
            connector.ClientID = source_element.ElementID
            connector.SupplierID = target_element.ElementID
            connector.Direction = "Source -> Destination"
            connector.Update()
            source_element.Connectors.Refresh()

            diagram_link = diagram.DiagramLinks.AddNew("", "")
            diagram_link.ConnectorID = connector.ConnectorID
            try:
                diagram_link.Style = "Mode=3;TREE=OR;Hidden=0;"
            except Exception:
                pass
            diagram_link.Update()

        diagram.DiagramLinks.Refresh()

    def _generate_deployment_via_ea(
        self,
        repository,
        project_interface,
        package,
        architecture_data: dict,
        output_path: str,
    ) -> str:
        nodes = architecture_data.get("nodes", [])
        artifacts = architecture_data.get("artifacts", [])
        connections = architecture_data.get("connections", [])

        if len(nodes) < 2 or len(artifacts) < 1 or len(connections) < 1:
            raise Exception("Deployment diagrams require at least 2 nodes, 1 artifact or service, and 1 connection.")

        nodes, artifacts, connections = self._compact_deployment_scene(nodes, artifacts, connections)
        diagram = package.Diagrams.AddNew("Diagrama de Despliegue", "Deployment")
        diagram.Update()

        layout = self._build_deployment_layout(nodes, artifacts)
        scene_connections = self._build_deployment_scene_connections(nodes, artifacts, connections)
        elements_map = self._create_deployment_elements(package, diagram, nodes, artifacts, layout)
        self._create_deployment_connections(diagram, elements_map, scene_connections)

        diagram.Update()
        diagram.DiagramObjects.Refresh()
        diagram.DiagramLinks.Refresh()
        repository.ReloadDiagram(diagram.DiagramID)
        return self._export_diagram(project_interface, diagram, output_path)

    def _deployment_node_spec(self, node_type: str) -> Tuple[str, str]:
        if node_type == "execution_environment":
            return ("Node", "application server")
        if node_type == "database_node":
            return ("Node", "database server")
        if node_type == "external_node":
            return ("Node", "external system")
        if node_type == "device":
            return ("Device", "")
        return ("Node", "")

    def _deployment_artifact_spec(self, artifact_type: str) -> Tuple[str, str]:
        if artifact_type == "service":
            return ("Artifact", "service")
        if artifact_type == "database":
            return ("Artifact", "database")
        return ("Artifact", "")

    def _deployment_visual_role(self, node: dict, artifact_count: int) -> str:
        node_type = str(node.get("type", "node"))
        normalized = str(node.get("name", "")).strip().casefold()

        if node_type == "device":
            return "client"
        if node_type == "database_node":
            return "database"
        if any(token in normalized for token in ("payment", "pasarela", "provider", "third party", "extern")):
            return "external_integration"
        if any(token in normalized for token in ("notif", "email", "smtp", "correo")):
            return "notification"
        if any(token in normalized for token in ("browser", "cliente", "navegador", "frontend")):
            return "client"
        if any(token in normalized for token in ("gateway", "web", "balancer", "balanceador", "lb")):
            return "web"
        if any(token in normalized for token in ("runtime", "jvm", "tomcat", "container", "docker", "k8s", "kubernetes")):
            return "app"
        if any(token in normalized for token in ("app", "backend", "api", "application", "aplicacion", "aplicaciones")):
            return "app"
        if artifact_count >= 3:
            return "app"
        return "node"

    def _deployment_visual_stereotype(self, node: dict, role: str) -> str:
        if role == "client":
            return "device" if node.get("type") == "device" else "external system"
        if role == "web":
            return "web server"
        if role == "app":
            return "application server"
        if role == "database":
            return "database server"
        if role == "notification":
            return "notification server"
        if role == "external_integration":
            return "external system"
        return self._deployment_node_spec(node.get("type", "node"))[1]

    def _deployment_visual_element_spec(self, node: dict, role: str) -> Tuple[str, str]:
        if role == "client":
            normalized = str(node.get("name", "")).strip().casefold()
            if node.get("type") == "device" or any(
                token in normalized for token in ("browser", "cliente", "navegador", "frontend")
            ):
                return ("Device", "device")
        element_type, fallback_stereotype = self._deployment_node_spec(node.get("type", "node"))
        stereotype = self._deployment_visual_stereotype(node, role) or fallback_stereotype
        return (element_type, stereotype)

    def _deployment_node_dimensions(self, artifact_count: int, is_primary_app: bool) -> Tuple[int, int]:
        node_width = self.DEPLOYMENT_NODE_BASE_WIDTH + (60 if is_primary_app else 0)
        node_height = max(
            self.DEPLOYMENT_NODE_HEIGHT,
            self.DEPLOYMENT_NODE_INSET_TOP
            + self.DEPLOYMENT_NODE_INSET_BOTTOM
            + artifact_count * self.DEPLOYMENT_ARTIFACT_HEIGHT
            + max(0, artifact_count - 1) * self.DEPLOYMENT_ARTIFACT_SPACING,
        )
        if is_primary_app:
            node_height = max(node_height, 320)
        return (node_width, node_height)

    def _compact_deployment_scene(
        self,
        nodes: List[dict],
        artifacts: List[dict],
        connections: List[dict],
    ) -> Tuple[List[dict], List[dict], List[dict]]:
        nodes_copy = [dict(node) for node in nodes]
        artifacts_copy = [dict(artifact) for artifact in artifacts]
        connections_copy = [dict(connection) for connection in connections]

        nodes_by_id = {node["id"]: node for node in nodes_copy}
        artifact_counts: Dict[str, int] = {}
        for artifact in artifacts_copy:
            artifact_counts[artifact["nodeId"]] = artifact_counts.get(artifact["nodeId"], 0) + 1

        node_roles = {
            node["id"]: self._deployment_visual_role(node, artifact_counts.get(node["id"], 0))
            for node in nodes_copy
        }

        web_hosts = [node for node in nodes_copy if node_roles.get(node["id"]) == "web"]
        preferred_web_host = web_hosts[0] if web_hosts else None
        if preferred_web_host:
            for artifact in artifacts_copy:
                artifact_name = str(artifact.get("name", "")).strip().casefold()
                current_node_id = artifact.get("nodeId", "")
                if node_roles.get(current_node_id) != "client":
                    continue
                if any(token in artifact_name for token in ("frontend", "front-end", "spa", "web app", "webapp")):
                    artifact["nodeId"] = preferred_web_host["id"]

        app_nodes = [
            node
            for node in nodes_copy
            if node_roles.get(node["id"]) == "app"
        ]
        runtime_nodes = [node for node in app_nodes if node.get("type") == "execution_environment"]
        host_nodes = [node for node in app_nodes if node.get("type") != "execution_environment"]

        direct_pairs = {
            (connection.get("from"), connection.get("to"))
            for connection in connections_copy
        }

        replacements: Dict[str, str] = {}
        removed_node_ids: Set[str] = set()

        for runtime in runtime_nodes:
            runtime_id = runtime["id"]
            runtime_artifacts = artifact_counts.get(runtime_id, 0)
            if runtime_artifacts < 1:
                continue

            runtime_name = str(runtime.get("name", "")).strip()
            runtime_parent = str(runtime.get("parentId", "")).strip()
            best_host = None

            for host in host_nodes:
                host_id = host["id"]
                if host_id in removed_node_ids or artifact_counts.get(host_id, 0) > 0:
                    continue

                host_name = str(host.get("name", "")).strip().casefold()
                if runtime_parent and runtime_parent == host_id:
                    best_host = host
                    break
                if host.get("parentId") == runtime_id:
                    best_host = host
                    break
                if (host_id, runtime_id) in direct_pairs or (runtime_id, host_id) in direct_pairs:
                    best_host = host
                    break
                if any(token in host_name for token in ("application", "aplicacion", "aplicaciones", "app server", "backend")):
                    best_host = host

            if not best_host:
                continue

            host_id = best_host["id"]
            host_environment = str(best_host.get("environment", "")).strip()
            if runtime_name and runtime_name.casefold() not in host_environment.casefold():
                best_host["environment"] = f"{host_environment} / {runtime_name}".strip(" /")

            for artifact in artifacts_copy:
                if artifact.get("nodeId") == runtime_id:
                    artifact["nodeId"] = host_id

            replacements[runtime_id] = host_id
            removed_node_ids.add(runtime_id)

        if not replacements:
            return nodes_copy, artifacts_copy, connections_copy

        merged_connections: Dict[Tuple[str, str, str], dict] = {}
        for connection in connections_copy:
            source = replacements.get(connection.get("from"), connection.get("from"))
            target = replacements.get(connection.get("to"), connection.get("to"))
            if not source or not target or source == target:
                continue

            label = str(connection.get("label", "")).strip()
            key = (source, target, label)
            merged_connections[key] = {
                "from": source,
                "to": target,
                "label": label,
            }

        compacted_nodes = [node for node in nodes_copy if node["id"] not in removed_node_ids]
        return compacted_nodes, artifacts_copy, list(merged_connections.values())

    def _build_deployment_layout(
        self,
        nodes: List[dict],
        artifacts: List[dict],
    ) -> Dict[str, Dict[str, Dict[str, object]]]:
        artifacts_by_node: Dict[str, List[dict]] = {}
        for artifact in artifacts:
            artifacts_by_node.setdefault(artifact["nodeId"], []).append(artifact)

        node_boxes: Dict[str, Dict[str, int]] = {}
        artifact_boxes: Dict[str, Dict[str, int]] = {}
        node_roles = {
            node["id"]: self._deployment_visual_role(node, len(artifacts_by_node.get(node["id"], [])))
            for node in nodes
        }

        role_groups: Dict[str, List[dict]] = {
            "client": [],
            "web": [],
            "app": [],
            "database": [],
            "external_integration": [],
            "notification": [],
            "node": [],
        }
        for node in nodes:
            role_groups.setdefault(node_roles[node["id"]], []).append(node)

        primary_app = None
        if role_groups["app"]:
            primary_app = max(
                role_groups["app"],
                key=lambda node: (len(artifacts_by_node.get(node["id"], [])), len(node.get("name", ""))),
            )

        node_dimensions = {
            node["id"]: self._deployment_node_dimensions(
                len(artifacts_by_node.get(node["id"], [])),
                primary_app is not None and node["id"] == primary_app["id"],
            )
            for node in nodes
        }

        scene_positions: Dict[str, Tuple[int, int]] = {}
        current_client_x = self.DEPLOYMENT_NODE_X_START
        for node in role_groups["client"]:
            scene_positions[node["id"]] = (current_client_x, 120)
            current_client_x += self.DEPLOYMENT_NODE_BASE_WIDTH + 30

        current_web_x = 330
        for node in [*role_groups["web"], *role_groups["node"]]:
            scene_positions[node["id"]] = (current_web_x, 120)
            current_web_x += self.DEPLOYMENT_NODE_BASE_WIDTH + 40

        app_x = max(650, current_web_x + 120)
        app_y = self.DEPLOYMENT_NODE_Y_START
        secondary_app_y = 120
        for node in role_groups["app"]:
            if primary_app and node["id"] == primary_app["id"]:
                scene_positions[node["id"]] = (app_x, app_y)
            else:
                scene_positions[node["id"]] = (app_x + self.DEPLOYMENT_NODE_BASE_WIDTH + 80, secondary_app_y)
                secondary_app_y += self.DEPLOYMENT_NODE_HEIGHT + 40

        primary_app_width = (
            node_dimensions.get(primary_app["id"], (self.DEPLOYMENT_NODE_BASE_WIDTH, self.DEPLOYMENT_NODE_HEIGHT))[0]
            if primary_app
            else self.DEPLOYMENT_NODE_BASE_WIDTH
        )
        max_app_right = app_x + primary_app_width
        for node in role_groups["app"]:
            node_left, _ = scene_positions.get(node["id"], (app_x, app_y))
            node_width = node_dimensions.get(node["id"], (self.DEPLOYMENT_NODE_BASE_WIDTH, self.DEPLOYMENT_NODE_HEIGHT))[0]
            max_app_right = max(max_app_right, node_left + node_width)

        current_db_x = max(1030, max_app_right + 180)
        for node in role_groups["database"]:
            scene_positions[node["id"]] = (current_db_x, 120)
            current_db_x += self.DEPLOYMENT_NODE_BASE_WIDTH + 40

        primary_app_height = node_dimensions.get(primary_app["id"], (self.DEPLOYMENT_NODE_BASE_WIDTH, self.DEPLOYMENT_NODE_HEIGHT))[1] if primary_app else self.DEPLOYMENT_NODE_HEIGHT
        lower_y = (
            scene_positions[primary_app["id"]][1] + primary_app_height + 110
            if primary_app and primary_app["id"] in scene_positions
            else self.DEPLOYMENT_LOWER_ROW_Y
        )
        lower_y = max(lower_y, self.DEPLOYMENT_LOWER_ROW_Y)

        lower_left_x = app_x + 30
        for node in role_groups["external_integration"]:
            scene_positions[node["id"]] = (lower_left_x, lower_y)
            lower_left_x += self.DEPLOYMENT_NODE_BASE_WIDTH + 70

        lower_right_x = app_x + primary_app_width + 90
        for node in role_groups["notification"]:
            scene_positions[node["id"]] = (lower_right_x, lower_y + 10)
            lower_right_x += self.DEPLOYMENT_NODE_BASE_WIDTH + 70

        for node in nodes:
            node_artifacts = artifacts_by_node.get(node["id"], [])
            is_primary_app = primary_app is not None and node["id"] == primary_app["id"]
            node_width, node_height = node_dimensions[node["id"]]
            left, top = scene_positions.get(node["id"], (self.DEPLOYMENT_NODE_X_START, self.DEPLOYMENT_NODE_Y_START))
            node_boxes[node["id"]] = {
                "left": left,
                "top": top,
                "width": node_width,
                "height": node_height,
                "role": node_roles[node["id"]],
            }

            for index, artifact in enumerate(node_artifacts):
                artifact_boxes[artifact["id"]] = {
                    "left": left + self.DEPLOYMENT_NODE_INSET_X,
                    "top": top
                    + self.DEPLOYMENT_NODE_INSET_TOP
                    + index * (self.DEPLOYMENT_ARTIFACT_HEIGHT + self.DEPLOYMENT_ARTIFACT_SPACING),
                    "width": self.DEPLOYMENT_ARTIFACT_WIDTH,
                    "height": self.DEPLOYMENT_ARTIFACT_HEIGHT,
                }

        return {"nodes": node_boxes, "artifacts": artifact_boxes}

    def _resolve_deployment_scene_endpoint(
        self,
        entity_id: str,
        nodes_by_id: Dict[str, dict],
        artifacts_by_id: Dict[str, dict],
    ) -> str:
        if entity_id in artifacts_by_id:
            return artifacts_by_id[entity_id].get("nodeId", "")
        if entity_id in nodes_by_id:
            return entity_id
        return ""

    def _build_deployment_scene_connections(
        self,
        nodes: List[dict],
        artifacts: List[dict],
        connections: List[dict],
    ) -> List[dict]:
        nodes_by_id = {node["id"]: node for node in nodes}
        artifacts_by_id = {artifact["id"]: artifact for artifact in artifacts}
        aggregated: Dict[Tuple[str, str], Dict[str, object]] = {}

        for connection in connections:
            source = self._resolve_deployment_scene_endpoint(
                connection.get("from", ""),
                nodes_by_id,
                artifacts_by_id,
            )
            target = self._resolve_deployment_scene_endpoint(
                connection.get("to", ""),
                nodes_by_id,
                artifacts_by_id,
            )
            if not source or not target or source == target:
                continue

            key = (source, target)
            entry = aggregated.setdefault(key, {"from": source, "to": target, "labels": []})
            label = str(connection.get("label", "")).strip()
            if label and label not in entry["labels"]:
                entry["labels"].append(label)

        scene_connections: List[dict] = []
        for entry in aggregated.values():
            labels = entry["labels"]
            scene_connections.append(
                {
                    "from": entry["from"],
                    "to": entry["to"],
                    "label": " | ".join(labels) if labels else "",
                }
            )

        return scene_connections

    def _create_deployment_elements(
        self,
        package,
        diagram,
        nodes: List[dict],
        artifacts: List[dict],
        layout: Dict[str, Dict[str, Dict[str, object]]],
    ) -> Dict[str, object]:
        elements_map: Dict[str, object] = {}

        for node in nodes:
            role = layout["nodes"][node["id"]].get("role", "node")
            element_type, stereotype = self._deployment_visual_element_spec(node, role)
            element = package.Elements.AddNew(node["name"], element_type)
            if stereotype:
                element.Stereotype = stereotype
            notes_lines = []
            if node.get("environment"):
                notes_lines.append(f"Environment: {node['environment']}")
            if node.get("parentId"):
                notes_lines.append(f"Parent: {node['parentId']}")
            if notes_lines:
                element.Notes = "\n".join(notes_lines)
            element.Update()
            package.Elements.Refresh()

            box = layout["nodes"][node["id"]]
            diagram_object = diagram.DiagramObjects.AddNew(
                (
                    f"l={box['left']};r={box['left'] + box['width']};"
                    f"t={box['top']};b={box['top'] + box['height']};"
                ),
                "",
            )
            diagram_object.ElementID = element.ElementID
            diagram_object.Sequence = self.DEPLOYMENT_SEQUENCE_NODE
            diagram_object.Update()
            elements_map[node["id"]] = element

        for artifact in artifacts:
            element_type, stereotype = self._deployment_artifact_spec(artifact.get("type", "artifact"))
            element = package.Elements.AddNew(artifact["name"], element_type)
            if stereotype:
                element.Stereotype = stereotype
            element.Update()
            package.Elements.Refresh()

            box = layout["artifacts"][artifact["id"]]
            diagram_object = diagram.DiagramObjects.AddNew(
                (
                    f"l={box['left']};r={box['left'] + box['width']};"
                    f"t={box['top']};b={box['top'] + box['height']};"
                ),
                "",
            )
            diagram_object.ElementID = element.ElementID
            diagram_object.Sequence = self.DEPLOYMENT_SEQUENCE_ARTIFACT
            diagram_object.Update()
            elements_map[artifact["id"]] = element

        diagram.DiagramObjects.Refresh()
        return elements_map

    def _create_deployment_connections(
        self,
        diagram,
        elements_map: Dict[str, object],
        connections: List[dict],
    ) -> None:
        for connection in connections:
            source_element = elements_map.get(connection["from"])
            target_element = elements_map.get(connection["to"])
            if not source_element or not target_element:
                continue

            source_type = getattr(source_element, "Type", "")
            target_type = getattr(target_element, "Type", "")
            if source_type not in {"Node", "Device"} or target_type not in {"Node", "Device"}:
                continue

            connector = source_element.Connectors.AddNew(connection.get("label", ""), "Association")
            connector.ClientID = source_element.ElementID
            connector.SupplierID = target_element.ElementID
            connector.Direction = "Source -> Destination"
            connector.Update()
            source_element.Connectors.Refresh()

            diagram_link = diagram.DiagramLinks.AddNew("", "")
            diagram_link.ConnectorID = connector.ConnectorID
            try:
                diagram_link.Style = "Mode=3;TREE=OR;Hidden=0;"
            except Exception:
                pass
            diagram_link.Update()

        diagram.DiagramLinks.Refresh()

    def _generate_activity_via_ea(
        self,
        repository,
        project_interface,
        package,
        architecture_data: dict,
        output_path: str,
    ) -> str:
        lanes = architecture_data.get("lanes", [])
        nodes = architecture_data.get("nodes", [])
        flows = architecture_data.get("flows", [])

        if not nodes or not flows:
            raise Exception("Activity diagrams require nodes and flows.")

        diagram = package.Diagrams.AddNew("Diagrama de Actividad", "Activity")
        diagram.Update()

        layout = self._build_activity_layout(nodes, flows, lanes)
        elements_map = self._create_activity_nodes(package, diagram, nodes, layout)
        self._create_activity_control_flows(diagram, elements_map, flows)

        diagram.Update()
        diagram.DiagramObjects.Refresh()
        diagram.DiagramLinks.Refresh()
        repository.ReloadDiagram(diagram.DiagramID)
        return self._export_diagram(project_interface, diagram, output_path)

    def _build_activity_layout(
        self,
        nodes: List[dict],
        flows: List[dict],
        lanes: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, int]]:
        nodes_by_id = {node["id"]: node for node in nodes}
        outgoing = self._build_activity_outgoing_map(flows)
        incoming = self._build_activity_incoming_map(flows)
        lane_centers = self._build_activity_lane_centers(nodes, lanes or [])

        initial_node = next((node for node in nodes if node.get("type") == "initial"), None)
        if not initial_node:
            raise Exception("Activity diagrams require an initial node.")

        main_path = self._derive_activity_main_path(initial_node["id"], nodes_by_id, outgoing, incoming)
        main_path_set = set(main_path)

        placements: Dict[str, Dict[str, int]] = {}
        occupied_branch_lanes: Dict[int, List[Tuple[int, int]]] = {}
        max_top_y = self.ACTIVITY_START_Y

        for index, node_id in enumerate(main_path):
            width, height = self._activity_node_dimensions(nodes_by_id[node_id]["type"])
            top_y = self.ACTIVITY_START_Y + (index * self.ACTIVITY_MAIN_SPACING)
            placements[node_id] = {
                "center_x": self._resolve_activity_node_center_x(
                    nodes_by_id[node_id],
                    lane_centers,
                    self.ACTIVITY_CENTER_X,
                ),
                "top_y": top_y,
                "width": width,
                "height": height,
            }
            max_top_y = max(max_top_y, top_y)

        used_nodes: Set[str] = set(main_path)
        branch_side_toggle = -1

        for node_id in main_path:
            edges = outgoing.get(node_id, [])
            if len(edges) < 2:
                continue

            main_successor = self._select_activity_main_successor(
                node_id,
                edges,
                nodes_by_id,
                outgoing,
                incoming,
            )
            decision_y = placements[node_id]["top_y"]
            branch_edges = [edge for edge in edges if edge.get("to") != main_successor]
            branch_edges.sort(key=lambda edge: self._activity_branch_priority(edge.get("label", "")))

            for edge in branch_edges:
                side_score = self._activity_branch_priority(edge.get("label", ""))
                side = -1 if side_score < 0 else 1 if side_score > 0 else branch_side_toggle
                if side_score == 0:
                    branch_side_toggle *= -1

                branch_path = self._trace_activity_branch_path(
                    edge.get("to"),
                    nodes_by_id,
                    outgoing,
                    incoming,
                    main_path_set,
                    used_nodes,
                    side,
                )
                if not branch_path:
                    continue

                reentry_target = self._find_activity_branch_reentry_target(
                    branch_path,
                    outgoing,
                    main_path_set,
                )
                branch_top_positions = self._build_activity_branch_top_positions(
                    branch_path,
                    decision_y,
                    placements,
                    reentry_target,
                )
                branch_interval = self._activity_branch_interval(branch_path, branch_top_positions, nodes_by_id)

                for offset, branch_node_id in enumerate(branch_path, start=1):
                    width, height = self._activity_node_dimensions(nodes_by_id[branch_node_id]["type"])
                    branch_center_x = self._select_activity_branch_lane(
                        side,
                        branch_interval,
                        occupied_branch_lanes,
                    )
                    center_x = self._resolve_activity_branch_center_x(
                        source_node=nodes_by_id[node_id],
                        branch_node=nodes_by_id[branch_node_id],
                        side=side,
                        lane_centers=lane_centers,
                        fallback_x=branch_center_x,
                    )
                    placements[branch_node_id] = {
                        "center_x": center_x,
                        "top_y": branch_top_positions[branch_node_id],
                        "width": width,
                        "height": height,
                    }
                    used_nodes.add(branch_node_id)
                    max_top_y = max(max_top_y, placements[branch_node_id]["top_y"])

                occupied_branch_lanes.setdefault(center_x, []).append(branch_interval)

        for node in nodes:
            if node["id"] in placements:
                continue
            width, height = self._activity_node_dimensions(node["type"])
            max_top_y += self.ACTIVITY_MAIN_SPACING
            placements[node["id"]] = {
                "center_x": self._resolve_activity_node_center_x(
                    node,
                    lane_centers,
                    self.ACTIVITY_CENTER_X,
                ),
                "top_y": max_top_y,
                "width": width,
                "height": height,
            }

        self._rebalance_activity_fork_targets(
            nodes=nodes,
            outgoing=outgoing,
            placements=placements,
            lane_centers=lane_centers,
        )

        return placements

    def _build_activity_outgoing_map(self, flows: List[dict]) -> Dict[str, List[dict]]:
        outgoing: Dict[str, List[dict]] = {}
        for flow in flows:
            outgoing.setdefault(flow["from"], []).append(flow)
        return outgoing

    def _build_activity_incoming_map(self, flows: List[dict]) -> Dict[str, List[dict]]:
        incoming: Dict[str, List[dict]] = {}
        for flow in flows:
            incoming.setdefault(flow["to"], []).append(flow)
        return incoming

    def _build_activity_lane_centers(
        self,
        nodes: List[dict],
        lanes: List[str],
    ) -> Dict[str, int]:
        ordered_lanes: List[str] = []
        seen = set()

        for lane in lanes:
            lane_name = str(lane or "").strip()
            if lane_name and lane_name.casefold() not in seen:
                seen.add(lane_name.casefold())
                ordered_lanes.append(lane_name)

        for node in nodes:
            lane_name = str(node.get("lane") or "").strip()
            if lane_name and lane_name.casefold() not in seen:
                seen.add(lane_name.casefold())
                ordered_lanes.append(lane_name)

        if not ordered_lanes:
            return {}

        start_x = self.ACTIVITY_CENTER_X - ((len(ordered_lanes) - 1) * self.ACTIVITY_LANE_GAP) // 2
        return {
            lane_name: start_x + (index * self.ACTIVITY_LANE_GAP)
            for index, lane_name in enumerate(ordered_lanes)
        }

    def _resolve_activity_node_center_x(
        self,
        node: dict,
        lane_centers: Dict[str, int],
        default_x: int,
    ) -> int:
        lane_name = str(node.get("lane") or "").strip()
        if lane_name and lane_name in lane_centers:
            return lane_centers[lane_name]
        return default_x

    def _resolve_activity_branch_center_x(
        self,
        source_node: dict,
        branch_node: dict,
        side: int,
        lane_centers: Dict[str, int],
        fallback_x: int,
    ) -> int:
        branch_lane = str(branch_node.get("lane") or "").strip()
        source_lane = str(source_node.get("lane") or "").strip()

        if source_node.get("type") == "fork":
            base_x = lane_centers.get(branch_lane, self.ACTIVITY_CENTER_X)
            if not branch_lane or branch_lane == source_lane:
                return base_x + (side * self.ACTIVITY_PARALLEL_OFFSET)
            return base_x

        if source_node.get("type") == "decision":
            if not branch_lane or branch_lane == source_lane:
                return fallback_x
            return lane_centers.get(branch_lane, fallback_x)

        return self._resolve_activity_node_center_x(branch_node, lane_centers, fallback_x)

    def _rebalance_activity_fork_targets(
        self,
        nodes: List[dict],
        outgoing: Dict[str, List[dict]],
        placements: Dict[str, Dict[str, int]],
        lane_centers: Dict[str, int],
    ) -> None:
        nodes_by_id = {node["id"]: node for node in nodes}

        for node in nodes:
            if node.get("type") != "fork" or node["id"] not in placements:
                continue

            branch_edges = outgoing.get(node["id"], [])
            branch_targets = [edge.get("to") for edge in branch_edges if edge.get("to") in placements]
            if len(branch_targets) < 2:
                continue

            fork_center_x = placements[node["id"]]["center_x"]
            fork_top_y = placements[node["id"]]["top_y"]
            branch_top_y = fork_top_y + self.ACTIVITY_BRANCH_OFFSET + self.ACTIVITY_BRANCH_SPACING

            for index, target_id in enumerate(branch_targets):
                target_node = nodes_by_id.get(target_id)
                if not target_node:
                    continue

                target_lane = str(target_node.get("lane") or "").strip()
                base_x = lane_centers.get(target_lane, fork_center_x)
                offset = ((index * 2) - (len(branch_targets) - 1)) * (self.ACTIVITY_PARALLEL_OFFSET // 2)
                if not target_lane or target_lane == str(node.get("lane") or "").strip():
                    placements[target_id]["center_x"] = fork_center_x + offset
                else:
                    placements[target_id]["center_x"] = base_x
                placements[target_id]["top_y"] = branch_top_y

    def _derive_activity_main_path(
        self,
        start_node_id: str,
        nodes_by_id: Dict[str, dict],
        outgoing: Dict[str, List[dict]],
        incoming: Dict[str, List[dict]],
    ) -> List[str]:
        path: List[str] = []
        visited: Set[str] = set()
        current_id: Optional[str] = start_node_id

        while current_id and current_id not in visited and current_id in nodes_by_id:
            path.append(current_id)
            visited.add(current_id)

            edges = outgoing.get(current_id, [])
            if not edges:
                break

            next_id = self._select_activity_main_successor(
                current_id,
                edges,
                nodes_by_id,
                outgoing,
                incoming,
            )
            if not next_id or next_id in visited:
                break

            current_id = next_id

        return path

    def _select_activity_main_successor(
        self,
        current_id: str,
        edges: List[dict],
        nodes_by_id: Dict[str, dict],
        outgoing: Dict[str, List[dict]],
        incoming: Dict[str, List[dict]],
    ) -> Optional[str]:
        if not edges:
            return None

        def edge_score(edge: dict) -> Tuple[int, int, int]:
            target_id = edge.get("to", "")
            return (
                self._activity_branch_priority(edge.get("label", "")),
                self._estimate_activity_reach(target_id, outgoing, set()),
                len(incoming.get(target_id, [])),
            )

        return max(edges, key=edge_score).get("to")

    def _trace_activity_branch_path(
        self,
        start_node_id: Optional[str],
        nodes_by_id: Dict[str, dict],
        outgoing: Dict[str, List[dict]],
        incoming: Dict[str, List[dict]],
        main_path_set: Set[str],
        used_nodes: Set[str],
        side: int,
    ) -> List[str]:
        branch_path: List[str] = []
        current_id = start_node_id
        local_visited: Set[str] = set()

        while current_id and current_id in nodes_by_id:
            if current_id in local_visited or current_id in used_nodes or current_id in main_path_set:
                break

            branch_path.append(current_id)
            local_visited.add(current_id)

            edges = outgoing.get(current_id, [])
            if not edges:
                break

            next_id = self._select_activity_branch_successor(edges, outgoing, incoming, side)
            if not next_id or next_id in main_path_set:
                break

            current_id = next_id

        return branch_path

    def _select_activity_branch_successor(
        self,
        edges: List[dict],
        outgoing: Dict[str, List[dict]],
        incoming: Dict[str, List[dict]],
        side: int,
    ) -> Optional[str]:
        if not edges:
            return None

        def edge_score(edge: dict) -> Tuple[int, int, int]:
            label_score = self._activity_branch_priority(edge.get("label", ""))
            signed_score = label_score if side > 0 else -label_score
            target_id = edge.get("to", "")
            return (
                signed_score,
                self._estimate_activity_reach(target_id, outgoing, set()),
                len(incoming.get(target_id, [])),
            )

        return max(edges, key=edge_score).get("to")

    def _estimate_activity_reach(
        self,
        node_id: str,
        outgoing: Dict[str, List[dict]],
        visited: Set[str],
    ) -> int:
        if not node_id or node_id in visited:
            return 0

        visited.add(node_id)
        best = 1
        for edge in outgoing.get(node_id, []):
            best = max(best, 1 + self._estimate_activity_reach(edge.get("to", ""), outgoing, visited.copy()))
        return best

    def _activity_branch_priority(self, label: str) -> int:
        normalized = (label or "").strip().lower()
        if not normalized:
            return 0

        positive_tokens = (
            "[si",
            "[sí",
            "si]",
            "sí]",
            "yes",
            "ok",
            "aprob",
            "valido",
            "válido",
            "exito",
            "éxito",
        )
        negative_tokens = (
            "[no",
            "no]",
            "error",
            "inval",
            "invál",
            "retry",
            "reintent",
            "fall",
            "sin ",
        )

        if any(token in normalized for token in positive_tokens):
            return 2
        if any(token in normalized for token in negative_tokens):
            return -2
        return 0

    def _find_activity_branch_reentry_target(
        self,
        branch_path: List[str],
        outgoing: Dict[str, List[dict]],
        main_path_set: Set[str],
    ) -> Optional[str]:
        for node_id in branch_path:
            for edge in outgoing.get(node_id, []):
                if edge.get("to") in main_path_set:
                    return edge.get("to")
        return None

    def _build_activity_branch_top_positions(
        self,
        branch_path: List[str],
        decision_y: int,
        placements: Dict[str, Dict[str, int]],
        reentry_target: Optional[str],
    ) -> Dict[str, int]:
        if not branch_path:
            return {}

        if reentry_target and reentry_target in placements:
            reentry_y = placements[reentry_target]["top_y"]
            direction = 1 if reentry_y > decision_y else -1
            first_top = decision_y + (direction * (self.ACTIVITY_BRANCH_OFFSET + 16))

            positions: Dict[str, int] = {}
            for index, node_id in enumerate(branch_path):
                positions[node_id] = first_top + (direction * index * self.ACTIVITY_BRANCH_SPACING)
            return positions

        positions = {}
        for index, node_id in enumerate(branch_path, start=1):
            positions[node_id] = decision_y + self.ACTIVITY_BRANCH_OFFSET + (index * self.ACTIVITY_BRANCH_SPACING)
        return positions

    def _activity_branch_interval(
        self,
        branch_path: List[str],
        branch_top_positions: Dict[str, int],
        nodes_by_id: Dict[str, dict],
    ) -> Tuple[int, int]:
        tops = []
        bottoms = []
        for node_id in branch_path:
            top_y = branch_top_positions[node_id]
            _, height = self._activity_node_dimensions(nodes_by_id[node_id]["type"])
            tops.append(top_y)
            bottoms.append(top_y + height)
        return (min(tops), max(bottoms))

    def _select_activity_branch_lane(
        self,
        side: int,
        branch_interval: Tuple[int, int],
        occupied_branch_lanes: Dict[int, List[Tuple[int, int]]],
    ) -> int:
        candidates = (
            [self.ACTIVITY_LEFT_X, self.ACTIVITY_LEFT_OUTER_X]
            if side < 0
            else [self.ACTIVITY_RIGHT_X, self.ACTIVITY_RIGHT_OUTER_X]
        )

        for lane_x in candidates:
            if self._activity_lane_is_available(lane_x, branch_interval, occupied_branch_lanes):
                return lane_x

        return candidates[-1]

    def _activity_lane_is_available(
        self,
        lane_x: int,
        branch_interval: Tuple[int, int],
        occupied_branch_lanes: Dict[int, List[Tuple[int, int]]],
    ) -> bool:
        start_y, end_y = branch_interval
        for occupied_start, occupied_end in occupied_branch_lanes.get(lane_x, []):
            separated = (
                end_y + self.ACTIVITY_BRANCH_CLEARANCE < occupied_start
                or start_y - self.ACTIVITY_BRANCH_CLEARANCE > occupied_end
            )
            if not separated:
                return False
        return True

    def _activity_node_dimensions(self, node_type: str) -> Tuple[int, int]:
        if node_type in {"fork", "join"}:
            return (self.ACTIVITY_SYNC_WIDTH, self.ACTIVITY_SYNC_HEIGHT)
        if node_type == "object":
            return (self.ACTIVITY_OBJECT_WIDTH, self.ACTIVITY_OBJECT_HEIGHT)
        if node_type == "decision":
            return (self.ACTIVITY_DECISION_WIDTH, self.ACTIVITY_DECISION_HEIGHT)
        if node_type in {"initial", "final"}:
            return (self.ACTIVITY_NODE_SIZE, self.ACTIVITY_NODE_SIZE)
        return (self.ACTIVITY_ACTION_WIDTH, self.ACTIVITY_ACTION_HEIGHT)

    def _activity_element_spec(self, node_type: str) -> Tuple[str, Optional[int]]:
        if node_type == "initial":
            return ("StateNode", 100)
        if node_type == "final":
            return ("StateNode", 101)
        if node_type in {"fork", "join"}:
            return ("Synchronization", None)
        if node_type == "object":
            return ("Object", None)
        if node_type == "decision":
            return ("Decision", None)
        return ("Action", None)

    def _create_activity_nodes(
        self,
        package,
        diagram,
        nodes: List[dict],
        layout: Dict[str, Dict[str, int]],
    ) -> Dict[str, object]:
        elements_map: Dict[str, object] = {}

        for node in nodes:
            ea_type, subtype = self._activity_element_spec(node["type"])
            element = package.Elements.AddNew(node["name"], ea_type)
            if subtype is not None:
                element.Subtype = subtype
            element.Update()
            package.Elements.Refresh()

            box = layout[node["id"]]
            left = box["center_x"] - round(box["width"] / 2)
            right = box["center_x"] + round(box["width"] / 2)
            top = box["top_y"]
            bottom = box["top_y"] + box["height"]

            diagram_object = diagram.DiagramObjects.AddNew(
                f"l={left};r={right};t={top};b={bottom};",
                "",
            )
            diagram_object.ElementID = element.ElementID
            diagram_object.Update()

            elements_map[node["id"]] = element

        diagram.DiagramObjects.Refresh()
        return elements_map

    def _create_activity_control_flows(
        self,
        diagram,
        elements_map: Dict[str, object],
        flows: List[dict],
    ) -> None:
        for flow in flows:
            source_element = elements_map.get(flow["from"])
            target_element = elements_map.get(flow["to"])
            if not source_element or not target_element:
                continue

            connector = source_element.Connectors.AddNew(flow.get("label", ""), "ControlFlow")
            connector.ClientID = source_element.ElementID
            connector.SupplierID = target_element.ElementID
            connector.Direction = "Source -> Destination"
            try:
                connector.RouteStyle = 2
            except Exception:
                pass
            connector.Update()
            source_element.Connectors.Refresh()

            try:
                diagram_link = diagram.DiagramLinks.AddNew("", "")
                diagram_link.ConnectorID = connector.ConnectorID
                diagram_link.Update()
            except Exception:
                pass

        diagram.DiagramLinks.Refresh()

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
