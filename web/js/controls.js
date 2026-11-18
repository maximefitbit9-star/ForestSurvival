// Player controls: keyboard + mouse (desktop) and virtual joystick + buttons (mobile).
"use strict";

class Controls {
  constructor(canvas, isMobile) {
    this.canvas = canvas;
    this.isMobile = !!isMobile;
    this.keys = {};
    this.moveInput = { x: 0, y: 0 };   // joystick vector (mobile)
    this.lookDelta = { x: 0, y: 0 };   // accumulated look for this frame
    this.sprintTouch = false;
    this.enabled = false;
    this.heading = 0;
    this.pitch = 0;
    this.sensitivity = 0.0022;

    window.addEventListener("keydown", (e) => {
      this.keys[e.key.toLowerCase()] = true;
      if (["w", "a", "s", "d", " "].includes(e.key.toLowerCase())) e.preventDefault();
    });
    window.addEventListener("keyup", (e) => { this.keys[e.key.toLowerCase()] = false; });

    if (!this.isMobile) {
      canvas.addEventListener("click", () => {
        if (this.enabled && document.pointerLockElement !== canvas) {
          canvas.requestPointerLock && canvas.requestPointerLock();
        }
      });
      document.addEventListener("mousemove", (e) => {
        if (document.pointerLockElement === canvas && this.enabled) {
          this.heading -= e.movementX * this.sensitivity;
          this.pitch = Math.max(-1.2, Math.min(1.2, this.pitch - e.movementY * this.sensitivity));
        }
      });
    } else {
      this._setupTouch();
    }
  }

  _setupTouch() {
    const joystick = document.getElementById("joystick");
    const knob = document.getElementById("joystick-knob");
    let activeId = null;
    let centre = null;
    const radius = () => joystick.offsetWidth / 2;

    const onStart = (e) => {
      for (const touch of e.changedTouches) {
        if (activeId === null) {
          activeId = touch.identifier;
          const rect = joystick.getBoundingClientRect();
          centre = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
          this._updateKnob(touch, centre, radius());
        }
      }
      e.preventDefault();
    };
    const onMove = (e) => {
      for (const touch of e.changedTouches) {
        if (touch.identifier === activeId) {
          this._updateKnob(touch, centre, radius());
        }
      }
      e.preventDefault();
    };
    const onEnd = (e) => {
      for (const touch of e.changedTouches) {
        if (touch.identifier === activeId) {
          activeId = null;
          this.moveInput.x = 0;
          this.moveInput.y = 0;
          knob.style.transform = "translate(-50%, -50%)";
        }
      }
    };
    joystick.addEventListener("touchstart", onStart, { passive: false });
    joystick.addEventListener("touchmove", onMove, { passive: false });
    joystick.addEventListener("touchend", onEnd);
    joystick.addEventListener("touchcancel", onEnd);

    // Look: any touch on the canvas outside the joystick rotates the camera.
    const canvas = this.canvas;
    let lookId = null, lastLook = null;
    canvas.addEventListener("touchstart", (e) => {
      for (const touch of e.changedTouches) {
        if (lookId === null) { lookId = touch.identifier; lastLook = { x: touch.clientX, y: touch.clientY }; }
      }
    }, { passive: true });
    canvas.addEventListener("touchmove", (e) => {
      for (const touch of e.changedTouches) {
        if (touch.identifier === lookId) {
          this.heading -= (touch.clientX - lastLook.x) * 0.006;
          this.pitch = Math.max(-1.2, Math.min(1.2, this.pitch - (touch.clientY - lastLook.y) * 0.006));
          lastLook = { x: touch.clientX, y: touch.clientY };
        }
      }
    }, { passive: true });
    canvas.addEventListener("touchend", (e) => {
      for (const touch of e.changedTouches) {
        if (touch.identifier === lookId) { lookId = null; }
      }
    }, { passive: true });
  }

  _updateKnob(touch, centre, radius) {
    let dx = touch.clientX - centre.x;
    let dy = touch.clientY - centre.y;
    const d = Math.hypot(dx, dy);
    if (d > radius) { dx = dx / d * radius; dy = dy / d * radius; }
    const knob = document.getElementById("joystick-knob");
    knob.style.transform = "translate(calc(-50% + " + dx + "px), calc(-50% + " + dy + "px))";
    this.moveInput.x = dx / radius;
    this.moveInput.y = -dy / radius;
  }

  setSprintButton(btn) {
    btn.addEventListener("touchstart", (e) => { this.sprintTouch = true; btn.classList.add("active"); e.preventDefault(); }, { passive: false });
    btn.addEventListener("touchend", () => { this.sprintTouch = false; btn.classList.remove("active"); });
  }

  moveVector() {
    if (this.isMobile) return this.moveInput;
    let x = 0, y = 0;
    if (this.keys["w"] || this.keys["arrowup"]) y += 1;
    if (this.keys["s"] || this.keys["arrowdown"]) y -= 1;
    if (this.keys["a"] || this.keys["arrowleft"]) x -= 1;
    if (this.keys["d"] || this.keys["arrowright"]) x += 1;
    const d = Math.hypot(x, y);
    if (d > 0) { x /= d; y /= d; }
    return { x, y };
  }

  isSprinting() {
    if (this.isMobile) return this.sprintTouch && (Math.hypot(this.moveInput.x, this.moveInput.y) > 0.3);
    return !!(this.keys["shift"]);
  }

  isCrouching() { return !this.isMobile && !!(this.keys["control"] || this.keys["c"]); }
}

if (typeof module !== "undefined") module.exports = { Controls };
