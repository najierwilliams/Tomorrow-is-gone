using UnityEngine;
using UnityEngine.SceneManagement;

namespace TomorrowIsGone.Unity.Gameplay
{
    public sealed class BootstrapSceneController : MonoBehaviour
    {
        private const string PlayableScene = "PlayableTestScene";

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void EnsureBootstrapController()
        {
            var activeScene = SceneManager.GetActiveScene();
            if (activeScene.name != "BootstrapCoreIntegration")
            {
                return;
            }

            var root = new GameObject("BootstrapSceneController");
            DontDestroyOnLoad(root);
            root.AddComponent<BootstrapSceneController>();
        }

        private void Start()
        {
            SceneManager.LoadScene(PlayableScene, LoadSceneMode.Single);
        }
    }
}
