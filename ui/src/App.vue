<script setup lang="ts">
import HelloWorld from './components/HelloWorld.vue'
import { workerOperations } from './workers/worker-caller'
import { blackmanHarris, expInterp, hzToMel, inverseExpInterp, inverseLerp, lerp, melToHz, stepwiseInterp } from './math-util';
import { ref } from 'vue';
import { db } from './db';

workerOperations.getSpectrogram(1);
var firstLog = false;
function log(){
    firstLog = true;
}
var msg = ref("none");
async function start() {
    var audioNode: AudioNode;
    const audioContext = new window.AudioContext({ sampleRate: 44100 });
    var useMic = true;
    if (useMic){
        msg.value = "started";
        var stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioNode = audioContext.createMediaStreamSource(stream);
        handleRecording(stream);
    } else {
        var fileUrl = "c2toc7.wav"
        //var fileUrl = "261.63 c4.wav
        //var fileUrl = "RAINY NIGHT IN TALLINN - Ludwig Goransson (128).mp3";
        //var fileUrl = "How Firm a Foundation piano.mp3";
        const response = await fetch(fileUrl);
        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        var bufferNode = audioContext.createBufferSource();
        bufferNode.buffer = audioBuffer;
        audioNode = bufferNode;
        bufferNode.start(0);
    }

    const analyserNode = audioContext.createAnalyser();
    analyserNode.fftSize = 4096;

    audioNode.connect(analyserNode);
    analyserNode.connect(audioContext.destination);
    const fftDataArray = new Uint8Array(analyserNode.frequencyBinCount);
    const scaledDataArray = new Uint8Array(145);


    const canvas = <HTMLCanvasElement>document.getElementById("canvas")!;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    const ctx = canvas.getContext("2d")!;
    console.log("audioContext.sampleRate", audioContext.sampleRate);

    function drawFrequencyBins() {
        analyserNode.getByteFrequencyData(fftDataArray);
        copyToScaledData(fftDataArray, scaledDataArray, firstLog)
        // Clear the canvas before drawing new frame
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        var maxAmp = 255;

        if (false){ //frequency on the X axis
            // Define variables for drawing
            const barWidth = (canvas.width / scaledDataArray.length);
            let barHeight;
            let x = 0;
            // Loop through dataArray to draw each frequency bin
            for (let i = 0; i < scaledDataArray.length; i++) {
                barHeight = scaledDataArray[i];
    
                // Set color based on bar height
                ctx.fillStyle = `rgb(${barHeight + 100}, 50, 50)`;
                
                // Draw bar (x, y, width, height)
                ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
    
                // Move x for the next bar
                x += barWidth + 1;
            }
        } else { //frequency on the Y axis
            var barHeight = (canvas.height / scaledDataArray.length) - 1;
            var y = canvas.height;
            for (var i = 0; i < scaledDataArray.length; i++){
                var barWidth = canvas.width * (scaledDataArray[i] / maxAmp)
                ctx.fillStyle = `rgb(${barWidth + 100}, 50, 50)`;
                
                // Draw bar (x, y, width, height)
                ctx.fillRect(canvas.width - barWidth, y - barHeight, barWidth, barHeight);
    
                // Move x for the next bar
                y -= barHeight + 1;
            }
        }


        firstLog = false;

        requestAnimationFrame(drawFrequencyBins);
    }
    drawFrequencyBins();
}

function handleRecording(stream: MediaStream): void {
    const mediaRecorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];

    mediaRecorder.ondataavailable = (event: BlobEvent) => {
        chunks.push(event.data);
    };

    mediaRecorder.onstop = () => {
        msg.value = "stopped";
        const blob = new Blob(chunks, { type: 'audio/webm' });

        // Store the blob in IndexedDB
        db.set('latestRecording', blob)
            .then(() => console.log('Recording saved successfully'))
            .catch((err) => console.error('Error saving recording:', err));
    };

    mediaRecorder.start();
    setTimeout(() => mediaRecorder.stop(), 5000); // Record for 10 seconds
}

function playRecording(): void {
    msg.value = "play recording";
    db.get('latestRecording')
        .then((blob: Blob) => {
            const audioURL = URL.createObjectURL(blob);
            const audio = new Audio(audioURL);
            audio.play();
        })
}


function copyToScaledData(fftDataArray: Float32Array | Uint8Array, scaledDataArray: Uint8Array, log: boolean){
    var minFrequencyHz = 58.27 //bflat1
    var maxFrequencyHz = 3729.31 //bflat7
    //via manual testing, it seems that these values cause the C notes to be correctly aligned
    var minFrequencyHz = 55
    var maxFrequencyHz = 3450
    var sampleRate = 44100
    var windowSize = 4096

    // if (Math.random() < 0.1){
    //     var minValue = Infinity;
    //     var maxValue = -Infinity
    //     for (var i = 5; i < 320; i++){
    //         minValue = Math.min(minValue, Math.round(fftDataArray[i]));
    //         maxValue = Math.max(maxValue, Math.round(fftDataArray[i]));
    //     }
    //     console.log("min: " + minValue, "max: " + maxValue);
    // }
    for (var i = 0; i < scaledDataArray.length; i++){
        var percent = inverseLerp(0, scaledDataArray.length - 1, i);
        var hz = expInterp(minFrequencyHz, maxFrequencyHz, percent)
        var n = (hz * windowSize) / sampleRate;
        var scaledAmplitude = stepwiseInterp(fftDataArray, n) * 0.6 + stepwiseInterp(fftDataArray, n-1) * 0.2 + stepwiseInterp(fftDataArray, n+1) * 0.2;
        if (firstLog){
            console.log(i, hz, n, fftDataArray[Math.floor(n)], fftDataArray[Math.ceil(n)])
        }
        if (log){
            // console.log("i = " + i, "percent = " + percent, "hz = " + hz, "n = " + n, "scaledAmplitude = " + scaledAmplitude);
            // console.log("floor = " + fftDataArray[Math.floor(n)]);
        }
        scaledDataArray[i] = scaledAmplitude;
        // var uint = scaledAmplitude + 265;
        // scaledDataArray[i] = uint > 255 ? 255 : (uint < 0 ? 0 : uint);
    }
}


</script>

<template>
    <div>
        <button @click="start">start</button>
        <button @click="playRecording">playback</button>
        <button @click="log">log</button>
        <div>{{ msg }}</div>
    </div>
    <canvas style="height: 90vh; width: 50vw" id="canvas"></canvas>
</template>

<style scoped></style>
