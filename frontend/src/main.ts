import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'

createApp(App).use(createPinia()).mount('#app')

// CSS can't stop every native drag (selected text, Firefox images/links); nothing here uses native drag-and-drop.
window.addEventListener('dragstart', (e) => e.preventDefault())
