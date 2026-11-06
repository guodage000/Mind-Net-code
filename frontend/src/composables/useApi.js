import axios from 'axios'

const http = axios.create({ baseURL: '/api', timeout: 30000 })

// 笔记 id 是带中文和斜杠的相对路径，逐段编码，保留 /
const enc = id => id.split('/').map(encodeURIComponent).join('/')

export const notesApi = {
  tree: (sub = '') => http.get('/notes/tree', { params: { sub } }),
  get: (id) => http.get(`/notes/${enc(id)}`),
  create: (data) => http.post('/notes/', data),
  update: (id, data) => http.patch(`/notes/${enc(id)}`, data),
  delete: (id) => http.delete(`/notes/${enc(id)}`),
  backlinks: (id) => http.get(`/notes/${enc(id)}/backlinks`),
}

export const searchApi = {
  search: (q, tags = [], note_type = null, limit = 20, offset = 0) =>
    http.post('/search/', { q, tags, note_type, limit, offset }),
  tags: () => http.get('/search/tags'),
}

export const gitApi = {
  status: () => http.get('/git/status'),
  sync: () => http.post('/git/sync'),
}

export const taskApi = {
  list: () => http.get('/tasks'),
  setStatus: (id, status) => http.patch(`/tasks/${enc(id)}/status`, { status }),
  move: (id, parent_id) => http.patch(`/tasks/${enc(id)}/move`, { parent_id }),
}

export const importApi = {
  pick: () => http.get('/import/pick'),
  run: (payload) => http.post('/import/', payload),
}
