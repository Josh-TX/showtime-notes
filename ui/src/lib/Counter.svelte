<script>
    import { signalRService } from "../SignalR.svelte";

    const increment = () => {
        signalRService.add(1);
    };
</script>

<button onclick={increment}>
    count is {signalRService.count}
</button>
