using System;
using System.Collections.Generic;
using UnityEngine;

namespace TomorrowIsGone.Unity.CoreIntegration
{
    public sealed class MockAuthoritativeRuntimeClient : IAuthoritativeRuntimeClient
    {
        public event Action<AuthoritativeSnapshot> SnapshotReceived;

        private readonly HashSet<string> _allowedIntents = new(StringComparer.Ordinal)
        {
            "player.move",
            "player.interact",
            "player.use_item",
            "player.emit_sound",
            "player.respawn"
        };

        private readonly Dictionary<string, AuthoritativeZombieState> _zombies = new(StringComparer.Ordinal);
        private AuthoritativePlayerState _player;
        private int _tick;

        public void Connect(string localPlayerId)
        {
            _tick = 0;
            _player = new AuthoritativePlayerState
            {
                PlayerId = localPlayerId,
                Role = "survivor",
                Form = "human",
                Dead = false,
                Health = 100f,
                Stamina = 100f,
                Hunger = 20f,
                Thirst = 15f,
                Position = new Vector3(0f, 1f, 0f),
                EquippedWeapon = "weapon_pipe",
                Inventory = new[]
                {
                    new InventoryItem { ItemId = "weapon_pipe", Quantity = 1, Durability = 34f, MaxDurability = 40f },
                    new InventoryItem { ItemId = "water_bottle", Quantity = 2, Durability = 0f, MaxDurability = 0f }
                }
            };

            _zombies.Clear();
            _zombies["zombie_001"] = new AuthoritativeZombieState
            {
                ZombieId = "zombie_001",
                AiState = "wander",
                Dead = false,
                Health = 35f,
                Position = new Vector3(8f, 1f, 6f)
            };

            PublishSnapshot(new AuthoritativeEvent[0]);
        }

        public void SubmitIntent(ClientCommandIntent intent)
        {
            if (!_allowedIntents.Contains(intent.Topic))
            {
                return;
            }

            var emittedEvents = new List<AuthoritativeEvent>();
            switch (intent.Topic)
            {
                case "player.move":
                    _player.Position = new Vector3(intent.Payload.X, intent.Payload.Y, intent.Payload.Z);
                    _player.Stamina = Mathf.Max(0f, _player.Stamina - 0.2f);
                    emittedEvents.Add(new AuthoritativeEvent
                    {
                        EventId = $"evt_move_{_tick}",
                        EventType = "player_moved",
                        ActorId = _player.PlayerId,
                        TargetId = string.Empty,
                        NumericValue = _player.Stamina
                    });
                    break;

                case "player.interact":
                    if (intent.Payload.Action == "attack_player" && _zombies.TryGetValue(intent.Payload.TargetId, out var zombie))
                    {
                        zombie.Health = Mathf.Max(0f, zombie.Health - 15f);
                        zombie.AiState = zombie.Health <= 0f ? "dead" : "chase";
                        zombie.Dead = zombie.Health <= 0f;
                        _zombies[zombie.ZombieId] = zombie;
                        emittedEvents.Add(new AuthoritativeEvent
                        {
                            EventId = $"evt_hit_{_tick}",
                            EventType = zombie.Dead ? "zombie_died" : "combat_hit",
                            ActorId = _player.PlayerId,
                            TargetId = zombie.ZombieId,
                            NumericValue = zombie.Health
                        });
                    }
                    break;

                case "player.use_item":
                    if (intent.Payload.ItemId == "water_bottle")
                    {
                        _player.Thirst = Mathf.Max(0f, _player.Thirst - 8f);
                        emittedEvents.Add(new AuthoritativeEvent
                        {
                            EventId = $"evt_use_{_tick}",
                            EventType = "item_used",
                            ActorId = _player.PlayerId,
                            TargetId = intent.Payload.ItemId,
                            NumericValue = _player.Thirst
                        });
                    }
                    break;

                case "player.emit_sound":
                    if (_zombies.TryGetValue("zombie_001", out var state) && !state.Dead)
                    {
                        state.AiState = "investigate";
                        _zombies[state.ZombieId] = state;
                    }
                    break;

                case "player.respawn":
                    _player.Dead = false;
                    _player.Health = 100f;
                    _player.Position = new Vector3(intent.Payload.X, intent.Payload.Y, intent.Payload.Z);
                    emittedEvents.Add(new AuthoritativeEvent
                    {
                        EventId = $"evt_respawn_{_tick}",
                        EventType = "player_respawned",
                        ActorId = _player.PlayerId,
                        TargetId = string.Empty,
                        NumericValue = _player.Health
                    });
                    break;
            }

            PublishSnapshot(emittedEvents.ToArray());
        }

        public bool IsIntentAllowed(string topic)
        {
            return _allowedIntents.Contains(topic);
        }

        private void PublishSnapshot(AuthoritativeEvent[] emittedEvents)
        {
            _tick += 1;
            _player.Hunger = Mathf.Min(100f, _player.Hunger + 0.01f);
            _player.Thirst = Mathf.Min(100f, _player.Thirst + 0.02f);

            var snapshot = new AuthoritativeSnapshot
            {
                LocalPlayer = _player,
                VisiblePlayers = new[] { _player },
                Zombies = new List<AuthoritativeZombieState>(_zombies.Values).ToArray(),
                Events = emittedEvents,
                ActiveChunks = new[]
                {
                    new AuthoritativeChunkState { ChunkKey = "0:0:0", ChunkX = 0, ChunkY = 0, ChunkZ = 0, Active = true },
                    new AuthoritativeChunkState { ChunkKey = "1:0:0", ChunkX = 1, ChunkY = 0, ChunkZ = 0, Active = true },
                    new AuthoritativeChunkState { ChunkKey = "0:1:0", ChunkX = 0, ChunkY = 1, ChunkZ = 0, Active = true }
                },
                WorldTime = new AuthoritativeWorldTime
                {
                    Tick = _tick,
                    DayIndex = 0,
                    TickOfDay = _tick % 24000,
                    DayNightState = (_tick % 24000) < 12000 ? "day" : "night"
                },
                AllowedIntents = new[]
                {
                    "player.move",
                    "player.interact",
                    "player.use_item",
                    "player.emit_sound",
                    "player.respawn"
                }
            };
            snapshot.Metadata["runtime"] = "mock-authoritative-client";
            SnapshotReceived?.Invoke(snapshot);
        }
    }
}
