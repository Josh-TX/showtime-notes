<script>
    import { signalRService } from "../SignalR.svelte";
</script>

<div style="display: flex;">
    {#each signalRService.otherUserInfos as userInfo}
        <details class="dropdown" style="margin-bottom: 0;">
            <summary role={userInfo.displayName == signalRService.syncedToDisplayName ? "button" : undefined}>{userInfo.displayName}</summary>
            <ul>
                <li>
                    <a href="#" onclick={() => signalRService.sync(userInfo)}>Sync</a>
                </li>
            </ul>
        </details>
    {/each}
</div>
