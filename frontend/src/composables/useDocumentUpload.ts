import { ref, watch } from 'vue'

import { ApiError } from '@/api/client'
import { uploadDocument } from '@/api/documents'
import type {
  Document,
  DocumentType,
  ExtractionJob,
} from '@/api/types'
import { validateUploadFile } from '@/components/document/document-utils'

export interface DocumentUploadOutcome {
  document: Document
  job: ExtractionJob | null
  reused: boolean
}

export function useDocumentUpload() {
  const file = ref<File | null>(null)
  const docType = ref<DocumentType>('invoice')
  const title = ref('')
  const submitting = ref(false)
  const error = ref('')
  const outcome = ref<DocumentUploadOutcome | null>(null)

  watch(file, (value) => {
    if (value) {
      outcome.value = null
      error.value = ''
    }
  })

  watch([docType, title], () => {
    if (error.value) error.value = ''
  })

  async function submit(): Promise<DocumentUploadOutcome | null> {
    if (submitting.value) return null
    if (!file.value) {
      error.value = '请选择要上传的文件。'
      return null
    }

    const fileError = validateUploadFile(file.value)
    if (fileError) {
      error.value = fileError
      return null
    }

    submitting.value = true
    error.value = ''
    try {
      const response = await uploadDocument({
        file: file.value,
        doc_type: docType.value,
        title: title.value.trim() || undefined,
      })
      const result: DocumentUploadOutcome = {
        document: response.document,
        job: response.extraction_job,
        reused: response.reused === true,
      }
      outcome.value = result
      file.value = null
      title.value = ''
      return result
    } catch (caught) {
      error.value =
        caught instanceof ApiError
          ? caught.message
          : '上传失败，请稍后重试。'
      return null
    } finally {
      submitting.value = false
    }
  }

  return {
    file,
    docType,
    title,
    submitting,
    error,
    outcome,
    submit,
  }
}
