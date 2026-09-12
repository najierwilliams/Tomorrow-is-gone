using System;
using System.Collections.Generic;
using UnityEngine;

namespace TomorrowIsGone.Unity.CoreIntegration
{
    [Serializable]
    public struct ClientCommandIntent
    {
        public string CommandId;
        public string PlayerId;
        public string Topic;
        public IntentPayload Payload;
    }

    [Serializable]
    public struct IntentPayload
    {
        public float X;
        public float Y;
        public float Z;
        public float Scalar;
        public string Action;
        public string TargetId;
        public string ItemId;
        public string Extra;
    }

    [Serializable]
    public struct AuthoritativePlayerState
    {
        public string PlayerId;
        public string Role;
        public string Form;
        public bool Dead;
        public float Health;
        public float Stamina;
        public float Hunger;
        public float Thirst;
        public Vector3 Position;
        public string EquippedWeapon;
        public InventoryItem[] Inventory;
    }

    [Serializable]
    public struct InventoryItem
    {
        public string ItemId;
        public int Quantity;
        public float Durability;
        public float MaxDurability;
    }

    [Serializable]
    public struct AuthoritativeZombieState
    {
        public string ZombieId;
        public string AiState;
        public bool Dead;
        public float Health;
        public Vector3 Position;
    }

    [Serializable]
    public struct AuthoritativeChunkState
    {
        public string ChunkKey;
        public int ChunkX;
        public int ChunkY;
        public int ChunkZ;
        public bool Active;
    }

    [Serializable]
    public struct AuthoritativeWorldTime
    {
        public int Tick;
        public int DayIndex;
        public int TickOfDay;
        public string DayNightState;
    }

    [Serializable]
    public struct AuthoritativeEvent
    {
        public string EventId;
        public string EventType;
        public string ActorId;
        public string TargetId;
        public float NumericValue;
    }

    [Serializable]
    public sealed class AuthoritativeSnapshot
    {
        public AuthoritativePlayerState LocalPlayer;
        public AuthoritativePlayerState[] VisiblePlayers = Array.Empty<AuthoritativePlayerState>();
        public AuthoritativeZombieState[] Zombies = Array.Empty<AuthoritativeZombieState>();
        public AuthoritativeChunkState[] ActiveChunks = Array.Empty<AuthoritativeChunkState>();
        public AuthoritativeEvent[] Events = Array.Empty<AuthoritativeEvent>();
        public AuthoritativeWorldTime WorldTime;
        public string[] AllowedIntents = Array.Empty<string>();
        public Dictionary<string, string> Metadata = new Dictionary<string, string>();
    }

    public interface IAuthoritativeRuntimeClient
    {
        event Action<AuthoritativeSnapshot> SnapshotReceived;

        void Connect(string localPlayerId);
        void SubmitIntent(ClientCommandIntent intent);
        bool IsIntentAllowed(string topic);
    }
}
