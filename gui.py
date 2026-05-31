"""
GUI — Dear ImGui interface for Virtual Conductor.
"""

import cv2
import glfw
import imgui
import imgui.internal
from imgui.integrations.glfw import GlfwRenderer
import OpenGL.GL as gl

from tracker import MIDI_CC_OPTIONS
from gesture_collector import GestureCollector
from chuck_controller import ChuckController
from osc_controller import OscController
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

        # --- Routing State ---
        # landmark choice per param lives in the .cfg files (ChucK reads it at
        # startup); mode (slider/landmark) + slider position live in routing_state
        # and are sent to ChucK live over OSC.
        self.routing_landmarks = {
            module: routing_config.load_routing(module)
            for module in routing_config.MODULE_PARAMS
        }
        # Snapshot of what's on disk (.cfg) so we know when a landmark edit is
        # unsaved — the Save buttons stay disabled until the two differ.
        self.routing_landmarks_saved = {
            module: dict(params) for module, params in self.routing_landmarks.items()
        }
        self.routing_state = routing_config.load_state()
        self.routing_msg = ""

        # Control-plane OSC client (mode + slider). Targets the same endpoint
        # ChucK listens on; landmark data is sent separately by the tracker.
        self.osc_ctrl = OscController(
            self.osc_ip_buf,
            int(self.osc_port_buf) if self.osc_port_buf.isdigit() else 8000,
        )

    @staticmethod
    def _begin_disabled(disabled):
        """Grey out and make non-interactive everything until _end_disabled.
        pyimgui 2.0 has no begin_disabled(), so we use the internal item flag."""
        if disabled:
            imgui.internal.push_item_flag(imgui.internal.ITEM_DISABLED, True)
            imgui.push_style_var(imgui.STYLE_ALPHA, imgui.get_style().alpha * 0.5)

    @staticmethod
    def _end_disabled(disabled):
        if disabled:
            imgui.pop_style_var()
            imgui.internal.pop_item_flag()

    def _send_routing_osc(self):
        """Push every param's mode + slider value to ChucK. Sent every frame:
        idempotent and cheap, so it auto-resyncs whenever the VM (re)starts."""
        if not self.osc_enabled:
            return
        for module, params in routing_config.MODULE_PARAMS.items():
            for param, _default in params:
                st = self.routing_state[module][param]
                mode_flag = 1 if st["mode"] == "landmark" else 0
                self.osc_ctrl.send_value(f"/mode/{module}/{param}", mode_flag)
                # Slider reads left→right = low→high; the modules apply 1.0 - value,
                # so invert here to keep the slider intuitive (landmarks stay as-is).
                self.osc_ctrl.send_value(f"/slider/{module}/{param}", 1.0 - float(st["slider"]))

    def _render_instrument_windows(self):
        """One 'ChucK Scripts' window with a collapsible section per *active*
        instrument, so the panel only shows what's currently loaded in the VM."""
        state_changed = False

        imgui.begin("Active ChucK Scripts")

        # Only instruments currently added to the VM get a routing section.
        # MODULE_PARAMS keys are lowercase ("synth"); ChucK effect names are
        # capitalized ("Synth").
        active = [
            (module, params)
            for module, params in routing_config.MODULE_PARAMS.items()
            if self.chuck.is_active(module.capitalize())
        ]

        if not active:
            imgui.text_disabled("No instruments active.")
        else:
            for module, params in active:
                # The triangle on a collapsing header minimizes/expands the section.
                header = imgui.collapsing_header(
                    module.capitalize(), flags=imgui.TREE_NODE_DEFAULT_OPEN
                )
                expanded = header[0] if isinstance(header, tuple) else header
                if expanded and self._render_instrument_section(module, params):
                    state_changed = True

        if self.routing_msg:
            imgui.text(self.routing_msg)

        imgui.end()

        if state_changed:
            routing_config.save_state(self.routing_state)

        # Keep ChucK in sync with the current mode/slider state.
        self._send_routing_osc()

    def _render_instrument_section(self, module, params):
        """Render one instrument's param rows + Save buttons inside its header.
        Returns True if a mode/slider value changed (so it gets persisted)."""
        state_changed = False

        # Column header labels
        imgui.text_disabled("Param")
        imgui.same_line(90)
        imgui.text_disabled("Slider")
        imgui.same_line(270)
        imgui.text_disabled("Landmark")
        imgui.same_line(450)
        imgui.text_disabled("Mode")
        imgui.separator()

        for param, _default in params:
            st = self.routing_state[module][param]
            is_landmark = st["mode"] == "landmark"

            # Param label
            imgui.text(param)
            imgui.same_line(90)

            # Slider (active in slider mode, greyed in landmark mode)
            self._begin_disabled(is_landmark)
            imgui.set_next_item_width(160)
            # format="" hides the numeric readout — the 0..1 value is just
            # wire data, meaningless to the user; only the grab position matters.
            s_changed, new_val = imgui.slider_float(
                f"##slider_{module}_{param}", st["slider"], 0.0, 1.0, format=""
            )
            self._end_disabled(is_landmark)
            if s_changed:
                st["slider"] = new_val
                state_changed = True

            imgui.same_line(270)

            # Landmark combo (active in landmark mode, greyed in slider mode)
            current = self.routing_landmarks[module][param]
            try:
                idx = routing_config.LANDMARKS.index(current)
            except ValueError:
                idx = 0
            self._begin_disabled(not is_landmark)
            imgui.set_next_item_width(160)
            c_changed, new_idx = imgui.combo(
                f"##lm_{module}_{param}", idx, routing_config.LANDMARKS
            )
            self._end_disabled(not is_landmark)
            if c_changed:
                self.routing_landmarks[module][param] = routing_config.LANDMARKS[new_idx]

            imgui.same_line(450)

            # Mode checkbox: checked = landmark, unchecked = slider (default)
            m_changed, checked = imgui.checkbox(
                f"landmark##{module}_{param}", is_landmark
            )
            if m_changed:
                st["mode"] = "landmark" if checked else "slider"
                state_changed = True

        imgui.spacing()

        # Landmark choice is read by ChucK at VM startup, so it's saved
        # explicitly (mode/slider are live and persist on their own). Save is
        # only enabled while the selection differs from the .cfg on disk.
        dirty = self.routing_landmarks[module] != self.routing_landmarks_saved[module]

        self._begin_disabled(not dirty)
        if imgui.button(f"Save Landmarks##{module}"):
            routing_config.save_routing(module, self.routing_landmarks[module])
            self.routing_landmarks_saved[module] = dict(self.routing_landmarks[module])
            self.routing_msg = f"Saved {module} landmarks to .cfg"
        if self.chuck.vm_running:
            imgui.same_line()
            if imgui.button(f"Save & Restart VM##{module}"):
                routing_config.save_routing(module, self.routing_landmarks[module])
                self.routing_landmarks_saved[module] = dict(self.routing_landmarks[module])
                self.chuck.restart_vm()  # re-adds whatever effects were playing
                self.routing_msg = f"Saved {module}, restarted VM"
        self._end_disabled(not dirty)

        if dirty and self.chuck.vm_running:
            imgui.text_colored("Restart VM to apply landmark changes.", 1.0, 0.8, 0.2)

        imgui.separator()
        return state_changed

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

        # --- Per-Instrument Routing Windows ---
        self._render_instrument_windows()

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
        self._render_instrument_windows()
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
