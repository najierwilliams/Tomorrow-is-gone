using System;
using System.Collections.Generic;
using TomorrowIsGone.Unity.CoreIntegration;
using TomorrowIsGone.Unity.Player;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace TomorrowIsGone.Unity.Gameplay
{
    public sealed class PlayableSceneController : MonoBehaviour
    {
        private const string LocalPlayerId = "unity_player";

        private IAuthoritativeRuntimeClient _runtimeClient;
        private IIntentInputSource _input;
        private readonly Dictionary<string, GameObject> _chunkViews = new(StringComparer.Ordinal);
        private readonly Dictionary<string, GameObject> _zombieViews = new(StringComparer.Ordinal);

        private GameObject _playerView;
        private Camera _camera;
        private Text _hud;
        private AuthoritativeSnapshot _snapshot;
        private float _intentTimer;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void EnsureController()
        {
            var activeScene = SceneManager.GetActiveScene();
            if (activeScene.name != "PlayableTestScene")
            {
                return;
            }

            var root = new GameObject("PlayableSceneController");
            root.AddComponent<PlayableSceneController>();
        }

        private void Start()
        {
            EnsureEnvironment();
            EnsureUi();

            _input = new CompositeIntentInputSource(
                new KeyboardMouseIntentInputSource(),
                new GamepadIntentInputSource());

            _runtimeClient = new MockAuthoritativeRuntimeClient();
            _runtimeClient.SnapshotReceived += OnSnapshotReceived;
            _runtimeClient.Connect(LocalPlayerId);
        }

        private void Update()
        {
            if (_runtimeClient == null)
            {
                return;
            }

            var movement = _input.ReadMovement();
            _intentTimer += Time.deltaTime;
            if (_intentTimer >= 0.08f && movement.sqrMagnitude > 0.02f)
            {
                _intentTimer = 0f;
                var delta = new Vector3(movement.x, 0f, movement.y).normalized * 1.5f;
                var target = _snapshot.LocalPlayer.Position + delta;
                _runtimeClient.SubmitIntent(new ClientCommandIntent
                {
                    CommandId = Guid.NewGuid().ToString("N"),
                    PlayerId = LocalPlayerId,
                    Topic = "player.move",
                    Payload = new IntentPayload { X = target.x, Y = target.y, Z = target.z }
                });
            }

            if (_input.AttackPressed())
            {
                _runtimeClient.SubmitIntent(new ClientCommandIntent
                {
                    CommandId = Guid.NewGuid().ToString("N"),
                    PlayerId = LocalPlayerId,
                    Topic = "player.interact",
                    Payload = new IntentPayload { Action = "attack_player", TargetId = "zombie_001" }
                });
            }

            if (_input.UseItemPressed())
            {
                _runtimeClient.SubmitIntent(new ClientCommandIntent
                {
                    CommandId = Guid.NewGuid().ToString("N"),
                    PlayerId = LocalPlayerId,
                    Topic = "player.use_item",
                    Payload = new IntentPayload { ItemId = "water_bottle" }
                });
            }

            if (_input.EmitSoundPressed())
            {
                _runtimeClient.SubmitIntent(new ClientCommandIntent
                {
                    CommandId = Guid.NewGuid().ToString("N"),
                    PlayerId = LocalPlayerId,
                    Topic = "player.emit_sound",
                    Payload = new IntentPayload { Scalar = 0.8f }
                });
            }

            if (_camera != null)
            {
                _camera.transform.position = _snapshot.LocalPlayer.Position + new Vector3(0f, 1.6f, -2.5f);
                _camera.transform.LookAt(_snapshot.LocalPlayer.Position + new Vector3(0f, 1.2f, 0f));
            }
        }

        private void OnDestroy()
        {
            if (_runtimeClient != null)
            {
                _runtimeClient.SnapshotReceived -= OnSnapshotReceived;
            }
        }

        private void OnSnapshotReceived(AuthoritativeSnapshot snapshot)
        {
            _snapshot = snapshot;
            RenderPlayer(snapshot.LocalPlayer);
            RenderZombies(snapshot.Zombies);
            RenderChunks(snapshot.ActiveChunks);
            RenderHud(snapshot);
        }

        private void EnsureEnvironment()
        {
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.name = "Ground";
            ground.transform.position = Vector3.zero;
            ground.transform.localScale = new Vector3(5f, 1f, 5f);

            var lightObject = new GameObject("Directional Light");
            var light = lightObject.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.2f;
            lightObject.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

            var cameraObject = new GameObject("PlayerCamera");
            _camera = cameraObject.AddComponent<Camera>();
            _camera.clearFlags = CameraClearFlags.Skybox;
            cameraObject.AddComponent<AudioListener>();
        }

        private void EnsureUi()
        {
            var canvasObject = new GameObject("HUDCanvas");
            var canvas = canvasObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasObject.AddComponent<CanvasScaler>();
            canvasObject.AddComponent<GraphicRaycaster>();

            var textObject = new GameObject("HUDText");
            textObject.transform.SetParent(canvasObject.transform, false);
            _hud = textObject.AddComponent<Text>();
            _hud.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            _hud.fontSize = 18;
            _hud.alignment = TextAnchor.UpperLeft;
            _hud.color = Color.white;

            var rect = _hud.rectTransform;
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = new Vector2(16f, -16f);
            rect.sizeDelta = new Vector2(900f, 460f);
        }

        private void RenderPlayer(AuthoritativePlayerState state)
        {
            if (_playerView == null)
            {
                _playerView = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                _playerView.name = "PlayerView";
                _playerView.GetComponent<Renderer>().material.color = new Color(0.1f, 0.8f, 0.2f);
            }

            _playerView.transform.position = state.Position;
        }

        private void RenderZombies(AuthoritativeZombieState[] zombies)
        {
            foreach (var zombie in zombies)
            {
                if (!_zombieViews.TryGetValue(zombie.ZombieId, out var view))
                {
                    view = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    view.name = $"ZombieView_{zombie.ZombieId}";
                    _zombieViews[zombie.ZombieId] = view;
                }

                view.transform.position = zombie.Position;
                var renderer = view.GetComponent<Renderer>();
                renderer.material.color = zombie.AiState switch
                {
                    "chase" => Color.red,
                    "investigate" => new Color(1f, 0.55f, 0f),
                    "dead" => Color.gray,
                    _ => new Color(0.6f, 0.9f, 0.2f)
                };
            }
        }

        private void RenderChunks(AuthoritativeChunkState[] chunks)
        {
            foreach (var chunk in chunks)
            {
                if (!_chunkViews.ContainsKey(chunk.ChunkKey))
                {
                    var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    go.name = $"Chunk_{chunk.ChunkKey}";
                    go.transform.localScale = new Vector3(10f, 0.2f, 10f);
                    go.GetComponent<Renderer>().material.color = new Color(0f, 0.35f, 0.9f, 0.35f);
                    _chunkViews[chunk.ChunkKey] = go;
                }

                _chunkViews[chunk.ChunkKey].transform.position = new Vector3(chunk.ChunkX * 10f, chunk.ChunkY * 2f - 1f, chunk.ChunkZ * 10f);
            }
        }

        private void RenderHud(AuthoritativeSnapshot snapshot)
        {
            if (_hud == null)
            {
                return;
            }

            var inventoryLines = new List<string>();
            foreach (var item in snapshot.LocalPlayer.Inventory)
            {
                var durability = item.MaxDurability > 0f ? $" ({item.Durability:0}/{item.MaxDurability:0})" : string.Empty;
                inventoryLines.Add($"- {item.ItemId} x{item.Quantity}{durability}");
            }

            var eventSummary = snapshot.Events.Length > 0
                ? snapshot.Events[snapshot.Events.Length - 1].EventType
                : "none";

            _hud.text =
                $"Role: {snapshot.LocalPlayer.Role} ({snapshot.LocalPlayer.Form})\n" +
                $"Health: {snapshot.LocalPlayer.Health:0.0}\n" +
                $"Stamina: {snapshot.LocalPlayer.Stamina:0.0}\n" +
                $"Hunger: {snapshot.LocalPlayer.Hunger:0.0}\n" +
                $"Thirst: {snapshot.LocalPlayer.Thirst:0.0}\n" +
                $"Equipped: {snapshot.LocalPlayer.EquippedWeapon}\n" +
                $"Inventory:\n{string.Join("\n", inventoryLines)}\n\n" +
                $"World Tick: {snapshot.WorldTime.Tick}\n" +
                $"Day/Night: {snapshot.WorldTime.DayNightState}\n" +
                $"Active Chunks: {snapshot.ActiveChunks.Length}\n" +
                $"Latest Event: {eventSummary}\n" +
                $"Allowed Intents: {string.Join(", ", snapshot.AllowedIntents)}\n\n" +
                "Controls:\nWASD / Left Stick = Move\nLeft Click / RB = Attack\nE / X = Use Item\nQ / B = Emit Sound";
        }
    }
}
