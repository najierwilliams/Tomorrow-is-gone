using UnityEngine;

namespace TomorrowIsGone.Unity.Player
{
    public interface IIntentInputSource
    {
        Vector2 ReadMovement();
        bool AttackPressed();
        bool UseItemPressed();
        bool EmitSoundPressed();
    }

    public sealed class KeyboardMouseIntentInputSource : IIntentInputSource
    {
        public Vector2 ReadMovement()
        {
            return new Vector2(Input.GetAxisRaw("Horizontal"), Input.GetAxisRaw("Vertical"));
        }

        public bool AttackPressed() => Input.GetMouseButtonDown(0);
        public bool UseItemPressed() => Input.GetKeyDown(KeyCode.E);
        public bool EmitSoundPressed() => Input.GetKeyDown(KeyCode.Q);
    }

    public sealed class GamepadIntentInputSource : IIntentInputSource
    {
        public Vector2 ReadMovement()
        {
            return new Vector2(Input.GetAxisRaw("Joystick X"), Input.GetAxisRaw("Joystick Y"));
        }

        public bool AttackPressed() => Input.GetKeyDown(KeyCode.JoystickButton5);
        public bool UseItemPressed() => Input.GetKeyDown(KeyCode.JoystickButton2);
        public bool EmitSoundPressed() => Input.GetKeyDown(KeyCode.JoystickButton1);
    }

    public sealed class CompositeIntentInputSource : IIntentInputSource
    {
        private readonly IIntentInputSource _primary;
        private readonly IIntentInputSource _secondary;

        public CompositeIntentInputSource(IIntentInputSource primary, IIntentInputSource secondary)
        {
            _primary = primary;
            _secondary = secondary;
        }

        public Vector2 ReadMovement()
        {
            var a = _primary.ReadMovement();
            var b = _secondary.ReadMovement();
            return b.sqrMagnitude > a.sqrMagnitude ? b : a;
        }

        public bool AttackPressed() => _primary.AttackPressed() || _secondary.AttackPressed();
        public bool UseItemPressed() => _primary.UseItemPressed() || _secondary.UseItemPressed();
        public bool EmitSoundPressed() => _primary.EmitSoundPressed() || _secondary.EmitSoundPressed();
    }
}
