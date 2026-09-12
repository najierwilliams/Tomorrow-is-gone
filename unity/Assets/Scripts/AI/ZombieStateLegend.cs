using System.Collections.Generic;

namespace TomorrowIsGone.Unity.AI
{
    public static class ZombieStateLegend
    {
        public static readonly IReadOnlyList<string> SupportedStates = new[]
        {
            "idle",
            "wander",
            "investigate",
            "detect_player",
            "chase",
            "attack",
            "search",
            "lose_target",
            "return_to_wandering",
            "dead"
        };
    }
}
