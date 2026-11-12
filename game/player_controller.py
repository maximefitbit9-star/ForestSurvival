"""First-person player controller: movement, camera, sprint, crouch, interaction."""
import math

from panda3d.core import Vec3, CollisionTraverser, CollisionNode, CollisionRay, CollisionHandlerQueue, BitMask32


class PlayerController:
    def __init__(self, base, gm, renderer, settings):
        self.base = base
        self.gm = gm
        self.renderer = renderer
        self.settings = settings
        self.keys = {}
        self.mouse_sensitivity = 0.12
        self.camera_height = 1.7
        self.crouch_height = 0.9
        self.heading = 0.0
        self.pitch = 0.0
        self.frozen = False
        self.base.disable_mouse()
        if self.base.camera is not None:
            self.base.camera.set_p(0)
        self.base.accept("wheel_up", self._zoom, [1])
        self.base.accept("wheel_down", self._zoom, [-1])

    def _zoom(self, direction):
        self.camera_height = max(0.9, min(4.0, self.camera_height - direction * 0.2))

    def bind_keys(self):
        for key in ("w", "a", "s", "d", "shift", "control", "space"):
            self.base.accept(key, self._set_key, [key, True])
            self.base.accept("%s-up" % key, self._set_key, [key, False])
            self.base.accept("arrow_up", self._set_key, ["w", True])
            self.base.accept("arrow_up-up", self._set_key, ["w", False])
            self.base.accept("arrow_down", self._set_key, ["s", True])
            self.base.accept("arrow_down-up", self._set_key, ["s", False])
            self.base.accept("arrow_left", self._set_key, ["a", True])
            self.base.accept("arrow_left-up", self._set_key, ["a", False])
            self.base.accept("arrow_right", self._set_key, ["d", True])
            self.base.accept("arrow_right-up", self._set_key, ["d", False])

    def _set_key(self, key, value):
        self.keys[key] = value

    def update(self, dt):
        if self.frozen or self.base.camera is None:
            return
        player = self.gm.player
        if self.base.win is None:
            return
        md = self.base.win.get_pointer(0)
        if self.base.win.move_pointer(0, self.base.win.get_x_size() // 2, self.base.win.get_y_size() // 2):
            if md.get_x() != self.base.win.get_x_size() // 2:
                self.heading -= (md.get_x() - self.base.win.get_x_size() // 2) * self.mouse_sensitivity
                self.pitch = max(-80, min(80, self.pitch - (md.get_y() - self.base.win.get_y_size() // 2) * self.mouse_sensitivity))
        dx, dy = 0.0, 0.0
        if self.keys.get("w"):
            dx += math.sin(math.radians(self.heading))
            dy += math.cos(math.radians(self.heading))
        if self.keys.get("s"):
            dx -= math.sin(math.radians(self.heading))
            dy -= math.cos(math.radians(self.heading))
        if self.keys.get("a"):
            dx -= math.cos(math.radians(self.heading))
            dy += math.sin(math.radians(self.heading))
        if self.keys.get("d"):
            dx += math.cos(math.radians(self.heading))
            dy -= math.sin(math.radians(self.heading))
        crouching = bool(self.keys.get("control"))
        sprinting = bool(self.keys.get("shift")) and not crouching and self.gm.player.stamina > 1
        speed = self.gm.player.walk_speed
        if sprinting:
            speed *= 1.75
        if crouching:
            speed *= 0.5
        terrain_speed_scale = 1.0
        if dx or dy:
            d = math.hypot(dx, dy)
            nx, ny = dx / d, dy / d
            player.x += nx * speed * dt
            player.y += ny * speed * dt
            player.moving = True
        else:
            player.moving = False
        player.sprinting = sprinting
        player.crouching = crouching
        half = self.gm.world.size / 2 - 5
        player.x = max(-half, min(half, player.x))
        player.y = max(-half, min(half, player.y))
        z = self.renderer.get_height(player.x, player.y)
        player.z = z
        height = self.crouch_height if crouching else self.camera_height
        self.base.camera.set_pos(player.x, player.y, z + height)
        self.base.camera.set_hpr(self.heading, self.pitch, 0)

    def forward_direction(self):
        return (math.sin(math.radians(self.heading)), math.cos(math.radians(self.heading)))
