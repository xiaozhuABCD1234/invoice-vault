import { createPinia } from 'pinia'
import { createApp } from 'vue'

import 'vue-sonner/style.css'
import './styles/theme.css'
import './styles/base.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

router
  .isReady()
  .then(() => {
    app.mount('#app')
  })
  .catch((error: unknown) => {
    console.error('路由初始化失败', error)
    app.mount('#app')
  })
