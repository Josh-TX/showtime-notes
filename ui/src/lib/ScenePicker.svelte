<script>
    import { signalRService } from "../SignalR.svelte";
    function addScene() {
        var name = prompt("name of new scene?");
        if (name) {
            signalRService.addScene(name);
        }
    }

    function goToNextScene() {
        const index = signalRService.sceneInfos.findIndex((i) => i.id === signalRService.selectedSceneId);
        signalRService.selectScene(signalRService.sceneInfos[index + 1].id);
    }

    function isLastSelected() {
        const index = signalRService.sceneInfos?.findIndex((i) => i.id === signalRService.selectedSceneId);
        return index === signalRService.sceneInfos?.length - 1;
    }
</script>

<article style="display: flex;">
    <div style="flex: 1; display: flex; gap: 0.5rem; overflow-x: auto; overflow-y: hidden; margin-right: var(--pico-block-spacing-horizontal)">
        {#each signalRService.sceneInfos as sceneInfo}
            <button
                class="outline {sceneInfo.id == signalRService.selectedSceneId ? '' : 'secondary'}"
                style="white-space: nowrap;"
                onclick={() => signalRService.selectScene(sceneInfo.id)}>{sceneInfo.name}</button
            >
        {/each}
        <button class="outline contrast" onclick={addScene} style="white-space: nowrap;">Add Scene</button>
    </div>
    <button disabled={isLastSelected()} onclick={goToNextScene}>Next Scene</button>
</article>
