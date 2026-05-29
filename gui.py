"""
GUI — Dear ImGui interface for Virtual Conductor.
"""

import cv2
import glfw
import imgui
from imgui.integrations.glfw import GlfwRenderer
import OpenGL.GL as gl

from tracker import MIDI_CC_OPTIONS
from gesture_collector import GestureCollector
from chuck_controller import ChuckController
import routing_config


class ConductorGUI:
    def __init__(self, width=1100, height=700, title="Virtual Conductor"):
        # --- GLFW + ImGui Init ---
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")

        self.window = glfw.create_window(width, height, title, None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Failed to create GLFW window")

        glfw.make_context_current(self.window)
        glfw.swap_interval(1)

        imgui.create_context()
        self.impl = GlfwRenderer(self.window)

        # --- Video Texture ---
        self.video_texture = self._create_texture()

        # --- Tracking State ---
        self.active_face = True
        self.active_hands = True
        self.active_pose = True

        # --- MIDI State ---
        self.lcc_index = 0
        self.rcc_index = 4
        self.cc_labels = [str(cc) for cc in MIDI_CC_OPTIONS]

        # --- OSC State ---
        self.osc_enabled = True
        self.osc_ip_buf = "127.0.0.1"
        self.osc_port_buf = "8000"

        # --- Gesture Collection State ---
        self.gesture_collector = GestureCollector()
        self.gesture_label_buf = ""
        self.gesture_train_msg = ""
        self._tracker_recognizer = None

        # --- ChucK ---
        self.chuck = ChuckController()

        # --- Routing State (landmark -> effect param, persisted to config/*.cfg) ---
        self.routing_state = {
            module: routing_config.load_routing(module)
            for module in routing_config.MODULE_PARAMS
        }
        self.routing_msg = ""

    def _render_routing_panel(self):
        imgui.begin("Routing")
        imgui.text("Map a hand landmark to each effect parameter.")
        imgui.spacing()

        for module, params in routing_config.MODULE_PARAMS.items():
            imgui.text_colored(module.upper(), 0.4, 0.8, 1.0)
            for param, _default in params:
                current = self.routing_state[module][param]
                try:
                    idx = routing_config.LANDMARKS.index(current)
                except ValueError:
                    idx = 0
                imgui.set_next_item_width(160)
                changed, new_idx = imgui.combo(
                    f"{param}##{module}", idx, routing_config.LANDMARKS
                )
                if changed:
                    self.routing_state[module][param] = routing_config.LANDMARKS[new_idx]
            imgui.spacing()

        imgui.separator()

        if imgui.button("Save Routing"):
            for module in routing_config.MODULE_PARAMS:
                routing_config.save_routing(module, self.routing_state[module])
            self.routing_msg = "Saved to config/*.cfg"

        if self.chuck.vm_running:
            imgui.same_line()
            if imgui.button("Save & Restart VM"):
                for module in routing_config.MODULE_PARAMS:
                    routing_config.save_routing(module, self.routing_state[module])
                self.chuck.restart_vm()  # re-adds whatever effects were playing
                self.routing_msg = "Saved and restarted VM"

        if self.routing_msg:
            imgui.text(self.routing_msg)

        # Routing is only read at VM startup, so a running VM needs a restart.
        if self.chuck.vm_running:
            imgui.text_colored("Restart VM to apply changes.", 1.0, 0.8, 0.2)

        imgui.end()

    def _render_chuck_panel(self):
        imgui.begin("ChucK")

        # Detect if VM died on its own
        if self.chuck.vm_poll() is not None and self.chuck._vm_proc is not None:
            self.chuck.log.append(f"[VM] Exited with code {self.chuck.vm_returncode}")
            self.chuck._vm_proc = None
            self.chuck._shred_ids.clear()

        # --- VM control ---
        if self.chuck.vm_running:
            imgui.text_colored("● VM", 0.3, 1.0, 0.3)
            imgui.same_line()
            if imgui.button("Stop VM"):
                self.chuck.stop_vm()
        else:
            imgui.text_colored("○ VM", 0.6, 0.6, 0.6)
            imgui.same_line()
            if imgui.button("Start VM"):
                self.chuck.start_vm()

        imgui.separator()

        # --- Per-effect toggles ---
        for name in self.chuck.effects:
            is_active = self.chuck.is_active(name)
            has_id    = self.chuck.has_id(name)

            if is_active:
                color = (0.3, 1.0, 0.3) if has_id else (1.0, 0.8, 0.2)  # green / yellow while pending
                imgui.text_colored(f"● {name}", *color)
                imgui.same_line()
                if has_id:
                    if imgui.button(f"Remove##{name}"):
                        self.chuck.remove_effect(name)
                else:
                    imgui.text_disabled("pending...")
            else:
                imgui.text_colored(f"○ {name}", 0.6, 0.6, 0.6)
                imgui.same_line()
                if self.chuck.vm_running:
                    if imgui.button(f"Add##{name}"):
                        self.chuck.add_effect(name)
                else:
                    imgui.text_disabled("--")

        imgui.separator()

        # --- Log ---
        imgui.begin_child("chuck_log", 0, 150, border=True)
        for line in list(self.chuck.log):
            imgui.text(line)
        imgui.set_scroll_here_y(1.0)
        imgui.end_child()

        imgui.end()

    def _create_texture(self):
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        return texture_id

    def _update_texture(self, frame_rgb):
        h, w = frame_rgb.shape[:2]
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.video_texture)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, gl.GL_RGB,
            w, h, 0,
            gl.GL_RGB, gl.GL_UNSIGNED_BYTE,
            frame_rgb
        )

    def set_recognizer(self, recognizer):
        self._tracker_recognizer = recognizer

    def _get_tracker_recognizer(self):
        return self._tracker_recognizer

    def should_close(self):
        return glfw.window_should_close(self.window)

    def begin_frame(self):
        glfw.poll_events()
        self.impl.process_inputs()

    def get_settings(self):
        active_modules = {
            "face": self.active_face,
            "hands": self.active_hands,
            "pose": self.active_pose
        }
        cc_settings = {
            "left": MIDI_CC_OPTIONS[self.lcc_index],
            "right": MIDI_CC_OPTIONS[self.rcc_index]
        }
        osc_settings = {
            "enabled": self.osc_enabled,
            "ip": self.osc_ip_buf.strip(),
            "port": int(self.osc_port_buf.strip()) if self.osc_port_buf.strip().isdigit() else 8000
        }
        return active_modules, cc_settings, osc_settings

    def render(self, frame_rgb, results, camera_warning=None):
        self._update_texture(frame_rgb)
        vid_h, vid_w = frame_rgb.shape[:2]

        imgui.new_frame()

        # --- Camera Feed ---
        imgui.begin("Camera Feed")
        if camera_warning:
            imgui.text_colored(camera_warning, 1.0, 0.3, 0.3)
        imgui.image(self.video_texture, vid_w, vid_h)
        imgui.end()

        # --- MIDI ---
        imgui.begin("MIDI")
        imgui.text("CC Assignment")
        imgui.set_next_item_width(120)
        _, self.lcc_index = imgui.combo("L-CC", self.lcc_index, self.cc_labels)
        imgui.same_line()
        imgui.set_next_item_width(120)
        _, self.rcc_index = imgui.combo("R-CC", self.rcc_index, self.cc_labels)
        imgui.end()

        # --- OSC ---
        imgui.begin("OSC")
        _, self.osc_enabled = imgui.checkbox("Enabled", self.osc_enabled)
        imgui.set_next_item_width(140)
        _, self.osc_ip_buf = imgui.input_text("IP", self.osc_ip_buf, 64)
        imgui.set_next_item_width(80)
        _, self.osc_port_buf = imgui.input_text("Port", self.osc_port_buf, 8)
        imgui.end()

        # --- Tracking ---
        imgui.begin("Tracking")

        _, self.active_hands = imgui.checkbox("Hands", self.active_hands)
        imgui.same_line()
        _, self.active_face = imgui.checkbox("Face", self.active_face)
        imgui.same_line()
        _, self.active_pose = imgui.checkbox("Pose", self.active_pose)

        imgui.separator()

        digits = [("Thumb", 4), ("Index", 8), ("Mid", 12), ("Ring", 16), ("Pinky", 20)]

        # Left Hand
        imgui.text_colored("LEFT HAND", 0.4, 0.8, 1.0)
        if not self.active_hands:
            imgui.text("[OFF]")
        elif results["left_hand"]:
            left_val = results["midi_values"]["left"] / 127.0
            imgui.progress_bar(left_val, (-1, 14), f"MIDI CC{MIDI_CC_OPTIONS[self.lcc_index]}: {results['midi_values']['left']}")
            for name, idx in digits:
                pt = results["left_hand"][idx]
                imgui.text(f"  {name}: {pt.x:.2f}, {pt.y:.2f}")
        else:
            imgui.text("  No Detection")

        imgui.spacing()

        # Right Hand
        imgui.text_colored("RIGHT HAND", 0.4, 1.0, 0.4)
        if not self.active_hands:
            imgui.text("[OFF]")
        elif results["right_hand"]:
            right_val = results["midi_values"]["right"] / 127.0
            imgui.progress_bar(right_val, (-1, 14), f"MIDI CC{MIDI_CC_OPTIONS[self.rcc_index]}: {results['midi_values']['right']}")
            for name, idx in digits:
                pt = results["right_hand"][idx]
                imgui.text(f"  {name}: {pt.x:.2f}, {pt.y:.2f}")
        else:
            imgui.text("  No Detection")

        imgui.spacing()

        # Face
        imgui.text_colored("FACE", 1.0, 1.0, 0.4)
        if not self.active_face:
            imgui.text("[OFF]")
        elif results["face"]:
            face = results["face"].face_landmarks[0]
            nose = face[1]
            imgui.text(f"  Nose: {nose.x:.2f}, {nose.y:.2f}")
            eye_l = face[33]
            eye_r = face[263]
            imgui.text(f"  L-Eye: {eye_l.x:.2f}, {eye_l.y:.2f}")
            imgui.text(f"  R-Eye: {eye_r.x:.2f}, {eye_r.y:.2f}")
            m_x = (face[13].x + face[14].x) / 2
            m_y = (face[13].y + face[14].y) / 2
            imgui.text(f"  Mouth: {m_x:.2f}, {m_y:.2f}")
        else:
            imgui.text("  No Detection")

        imgui.end()

        # --- Gesture Panel ---
        imgui.begin("Gestures")

        # Live recognition display
        rh_gesture = results.get("gesture", {}).get("right_hand")
        rh_conf = results.get("gesture_confidence", {}).get("right_hand", 0.0)
        if rh_gesture:
            imgui.text_colored(f"Right Hand: {rh_gesture} ({int(rh_conf * 100)}%)", 0.4, 1.0, 0.4)
        else:
            imgui.text("Right Hand: ---")

        imgui.separator()

        # Collection controls
        imgui.text("Collect Data")
        changed, self.gesture_label_buf = imgui.input_text("Label", self.gesture_label_buf, 64)

        status = self.gesture_collector.get_status()
        if status["recording"]:
            imgui.text_colored(f"Recording: {status['sample_count']} samples", 1.0, 0.3, 0.3)
            if imgui.button("Stop"):
                count = self.gesture_collector.stop_recording()
                self.gesture_train_msg = f"Saved {count} samples"
        else:
            label = self.gesture_label_buf.strip()
            if label and results.get("right_hand"):
                if imgui.button("Record"):
                    self.gesture_collector.start_recording(label, "right_hand")
                    self.gesture_train_msg = ""
            else:
                imgui.text_disabled("Enter label + show right hand")

        # Record samples each frame while recording
        if status["recording"] and results.get("right_hand"):
            self.gesture_collector.record_sample(results["right_hand"])

        imgui.spacing()

        # Train button
        if imgui.button("Train Model"):
            recognizer = self._get_tracker_recognizer()
            if recognizer:
                success, msg = recognizer.train("right_hand")
                self.gesture_train_msg = msg
            else:
                self.gesture_train_msg = "Trainer not available"

        if self.gesture_train_msg:
            imgui.text(self.gesture_train_msg)

        imgui.spacing()
        imgui.separator()

        # Dataset summary
        summary = self.gesture_collector.get_summary()
        if summary:
            imgui.text("Collected gestures:")
            to_delete = None
            for (source, label), count in sorted(summary.items()):
                imgui.text(f"  {source}/{label}: {count}")
                imgui.same_line()
                if imgui.small_button(f"X##{source}_{label}"):
                    to_delete = (label, source)
            if to_delete:
                self.gesture_collector.delete_gesture(*to_delete)

        imgui.end()

        # --- ChucK Panel ---
        self._render_chuck_panel()

        # --- Routing Panel ---
        self._render_routing_panel()

        # --- OpenGL Render ---
        imgui.render()
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self.impl.render(imgui.get_draw_data())
        glfw.swap_buffers(self.window)

    def render_no_frame(self, camera_warning=None):
        imgui.new_frame()
        imgui.begin("Camera Feed")
        imgui.text("No camera frame available.")
        if camera_warning:
            imgui.text_colored(camera_warning, 1.0, 0.3, 0.3)
        imgui.end()
        self._render_chuck_panel()
        self._render_routing_panel()
        imgui.render()
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self.impl.render(imgui.get_draw_data())
        glfw.swap_buffers(self.window)

    def shutdown(self):
        self.chuck.stop_vm()
        gl.glDeleteTextures(1, [self.video_texture])
        self.impl.shutdown()
        glfw.terminate()
