<script>
    import MyName from "./lib/MyName.svelte";
    import OtherUsers from "./lib/OtherUsers.svelte";
    import ScenePicker from "./lib/ScenePicker.svelte";
    import Timeline from "./lib/Timeline.svelte";
</script>

<header style="display: flex">
    <div style="flex: 1;">
        <OtherUsers />
    </div>
    <MyName />
</header>
<ScenePicker />
<main style="border: 3px solid blue; flex: 1;">
    <Timeline />
</main>

<style>
</style>
