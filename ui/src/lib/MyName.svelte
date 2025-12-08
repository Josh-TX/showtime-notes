<script>
    import { signalRService } from "../SignalR.svelte";
</script>

<details class="dropdown" style="margin-bottom: 0;">
    <summary>{signalRService.myUserInfo?.displayName}</summary>
    <ul>
        <li><a href="logout">Log out</a></li>
    </ul>
</details>
