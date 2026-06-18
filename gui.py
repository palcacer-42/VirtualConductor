"""
GUI — Dear ImGui interface for Virtual Conductor.
"""

import math

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

# Strength of the optional per-param "Exp" feel curve (normalized exponential
# y = (e^(k·x) − 1)/(e^k − 1)). Higher k = stronger bend. Tune by ear.
EXP_K = 2.0


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
        # Python owns all routing: per param it holds the mode (slider/landmark),
        # the slider position, and the chosen landmark, then sends one resolved
        # value to ChucK live over OSC. Everything persists in routing_state.
        self.routing_state = routing_config.load_state()

        # Input source selection ("fake-theorbo" or "mic"), persisted separately
        # from the per-param routing state.
        self.input_source = routing_config.load_input_source()

        # Last value seen for every landmark, updated each frame from the tracker.
        # Held between frames so a param freezes (rather than snapping to 0) when
        # its hand leaves view. Seeded to a neutral pose like ChucK used to.
        self.latest_landmarks = {
            lm: (0.0 if lm.endswith("_z") else 0.5)
            for lm in routing_config.LANDMARKS
        }

        # OSC client for the resolved per-param values ChucK plays.
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
        """Resolve each param to a single value and push it to ChucK on
        /param/<module>/<param>. Sent every frame: idempotent and cheap, so it
        auto-resyncs whenever the VM (re)starts."""
        if not self.osc_enabled:
            return
        # Contract: ChucK maps 0 -> param minimum, 1 -> maximum, no inversion.
        # All axis flips happen here so the value on the wire is always normalized.
        for module, params in routing_config.MODULE_PARAMS.items():
            for param, _default in params:
                st = self.routing_state[module][param]
                if st["mode"] == "landmark":
                    raw = self.latest_landmarks.get(st["landmark"], 0.5)
                    # Invert FIRST (fix the axis direction), then range on the
                    # corrected signal. This keeps Set Min/Max semantic: lo always
                    # maps to 0 (param min), hi to 1 (max). Captures live in this
                    # corrected space, so the range resets when invert toggles.
                    r = (1.0 - raw) if st["invert"] else raw
                    span = st["hi"] - st["lo"]
                    if abs(span) > 1e-6:
                        value = max(0.0, min(1.0, (r - st["lo"]) / span))
                    else:
                        value = 0.0
                else:
                    value = float(st["slider"])   # slider already reads low→high
                if st["exp"]:
                    # Feel knob: bend the final 0..1 through a normalized exp curve
                    # (same for slider and landmark). ChucK still maps linearly.
                    value = (math.exp(EXP_K * value) - 1.0) / (math.exp(EXP_K) - 1.0)
                self.osc_ctrl.send_value(f"/param/{module}/{param}", value)
        # Input source select: 0 = fake-theorbo, 1 = mic. Sent every frame like
        # the params, so it auto-resyncs whenever the VM (re)starts.
        self.osc_ctrl.send_value(
            "/param/input/source", 1.0 if self.input_source == "mic" else 0.0
        )

    def _render_instrument_windows(self):
        """One 'ChucK Scripts' window with a collapsible section per *active*
        instrument, so the panel only shows what's currently loaded in the VM."""
        state_changed = False

        imgui.begin("Active ChucK Scripts")

        # MODULE_PARAMS keys are lowercase ("synth"); ChucK effect names are
        # capitalized ("Synth"). Theorbo is the always-on input source (a core
        # shred, not an add/remove effect), so it shows whenever the VM runs;
        # other instruments appear only once added to the VM.
        active = []
        if self.chuck.vm_running and "input" in routing_config.MODULE_PARAMS:
            active.append(("input", routing_config.MODULE_PARAMS["input"]))
        active += [
            (module, params)
            for module, params in routing_config.MODULE_PARAMS.items()
            if module != "input" and self.chuck.is_active(module.capitalize())
        ]

        if not active:
            imgui.text_disabled("No instruments active.")
        else:
            for module, params in active:
                # The triangle on a collapsing header minimizes/expands the section.
                # Theorbo is the input source — show it as "Input".
                label = "Input" if module == "input" else module.capitalize()
                header = imgui.collapsing_header(
                    label, flags=imgui.TREE_NODE_DEFAULT_OPEN
                )
                expanded = header[0] if isinstance(header, tuple) else header
                if expanded and self._render_instrument_section(module, params):
                    state_changed = True

        imgui.end()

        if state_changed:
            routing_config.save_state(self.routing_state)

        # Push each param's resolved value (slider or landmark) to ChucK.
        self._send_routing_osc()

    def _render_instrument_section(self, module, params):
        """Render one instrument's param rows.
        Returns True if any routing value changed (so it gets persisted)."""
        state_changed = False

        # Input is slider-only — no landmark routing for it.
        if module == "input":
            # Source selector: switch between the fake-theorbo (looped wav) and
            # the live mic. Persisted on its own (not part of routing_state).
            imgui.text("source")
            imgui.same_line(60)
            for src in routing_config.INPUT_SOURCES:
                clicked = imgui.radio_button(
                    f"{src}##input_source", self.input_source == src
                )
                if clicked and self.input_source != src:
                    self.input_source = src
                    routing_config.save_input_source(src)
                imgui.same_line()
            imgui.new_line()
            imgui.separator()

            imgui.text_disabled("Param")
            imgui.same_line(60)
            imgui.text_disabled("Slider")
            imgui.same_line(240)
            imgui.text_disabled("Exp")
            imgui.separator()
            for param, _default in params:
                st = self.routing_state[module][param]
                imgui.text(param)
                imgui.same_line(60)
                imgui.set_next_item_width(160)
                s_changed, new_val = imgui.slider_float(
                    f"##slider_{module}_{param}", st["slider"], 0.0, 1.0, format=""
                )
                if s_changed:
                    st["slider"] = new_val
                    state_changed = True
                imgui.same_line(240)
                e_changed, exp_on = imgui.checkbox(f"##exp_{module}_{param}", st["exp"])
                if e_changed:
                    st["exp"] = exp_on
                    state_changed = True
            return state_changed

        # Column header labels
        imgui.text_disabled("Param")
        imgui.same_line(60)
        imgui.text_disabled("Slider")
        imgui.same_line(240)
        imgui.text_disabled("Landmark")
        imgui.same_line(420)
        imgui.text_disabled("Use")
        imgui.same_line(460)
        imgui.text_disabled("Inv")
        imgui.same_line(500)
        imgui.text_disabled("Range")
        imgui.same_line(750)
        imgui.text_disabled("Exp")
        imgui.separator()

        for param, _default in params:
            st = self.routing_state[module][param]
            is_landmark = st["mode"] == "landmark"

            # Param label
            imgui.text(param)
            imgui.same_line(60)

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

            imgui.same_line(240)

            # Landmark combo (active in landmark mode, greyed in slider mode).
            # Live: the change takes effect on the next frame, no VM restart.
            try:
                idx = routing_config.LANDMARKS.index(st["landmark"])
            except ValueError:
                idx = 0
            self._begin_disabled(not is_landmark)
            imgui.set_next_item_width(160)
            c_changed, new_idx = imgui.combo(
                f"##lm_{module}_{param}", idx, routing_config.LANDMARKS
            )
            self._end_disabled(not is_landmark)
            if c_changed:
                st["landmark"] = routing_config.LANDMARKS[new_idx]
                # The range was calibrated in the old landmark's space, so it's
                # meaningless on the new one — reset to the full span.
                st["lo"], st["hi"] = (
                    routing_config.DEFAULT_LO, routing_config.DEFAULT_HI
                )
                state_changed = True

            imgui.same_line(420)

            # Mode checkbox: checked = landmark, unchecked = slider (default)
            m_changed, checked = imgui.checkbox(
                f"##mode_{module}_{param}", is_landmark
            )
            if m_changed:
                st["mode"] = "landmark" if checked else "slider"
                state_changed = True

            imgui.same_line(460)

            # Invert checkbox: flips the landmark (1 - value). Only meaningful in
            # landmark mode — the slider already reads low→high — so it's greyed
            # out otherwise.
            self._begin_disabled(not is_landmark)
            i_changed, inverted = imgui.checkbox(
                f"##invert_{module}_{param}", st["invert"]
            )
            self._end_disabled(not is_landmark)
            if i_changed:
                st["invert"] = inverted
                # Captures live in the invert-corrected space, so flipping invert
                # invalidates them — reset to full span to recalibrate.
                st["lo"], st["hi"] = (
                    routing_config.DEFAULT_LO, routing_config.DEFAULT_HI
                )
                state_changed = True

            # Range calibration: always shown, greyed out unless this param is in
            # landmark mode (like Inv). Min/Max capture the live invert-corrected
            # value (lo = param min, hi = param max); the readout shows it live.
            raw = self.latest_landmarks.get(st["landmark"], 0.5)
            r = (1.0 - raw) if st["invert"] else raw
            imgui.same_line(500)
            self._begin_disabled(not is_landmark)
            imgui.text_disabled(f"{r:.2f}")
            imgui.same_line()
            if imgui.small_button(f"Min##{module}_{param}"):
                st["lo"] = r
                state_changed = True
            imgui.same_line()
            imgui.text_disabled(f"{st['lo']:.2f}")
            imgui.same_line()
            if imgui.small_button(f"Max##{module}_{param}"):
                st["hi"] = r
                state_changed = True
            imgui.same_line()
            imgui.text_disabled(f"{st['hi']:.2f}")
            imgui.same_line()
            if imgui.small_button(f"Rst##{module}_{param}"):
                st["lo"], st["hi"] = (
                    routing_config.DEFAULT_LO, routing_config.DEFAULT_HI
                )
                state_changed = True
            self._end_disabled(not is_landmark)

            # Exp checkbox: bends the final 0..1 through a feel curve. Applies to
            # both slider and landmark, so it stays enabled in both modes. Fixed
            # column after the range group.
            imgui.same_line(750)
            e_changed, exp_on = imgui.checkbox(f"##exp_{module}_{param}", st["exp"])
            if e_changed:
                st["exp"] = exp_on
                state_changed = True

        imgui.spacing()
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
        # Refresh only the landmarks seen this frame; the rest hold their last
        # value so params don't snap when a hand leaves view.
        if results:
            self.latest_landmarks.update(results.get("landmark_values", {}))

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
