'use client'

import { useState, useCallback, useEffect, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Upload, 
  FileImage, 
  Brain, 
  Eye, 
  CheckCircle, 
  AlertCircle,
  ArrowLeft,
  Download,
  Share,
  History,
  Cpu,
  Network,
  Sparkles
} from 'lucide-react'
import Link from 'next/link'
import ResultsDisplay from './ResultsDisplay'

interface UploadedFile {
  file: File
  preview: string
  id: string
}

interface ProcessingResult {
  id: string
  uploadId?: string // Store the actual upload ID for exports
  status: 'processing' | 'completed' | 'failed'
  progress: number
  currentStage?: 'tokenization' | 'semantic' | 'reconstruction' | 'complete'
  extractedText?: string
  glyphs?: Array<{
    symbol: string
    confidence: number
    position: { x: number; y: number; width: number; height: number }
    meaning?: string
    isReconstructed?: boolean
  }>
  translation?: string
  confidence?: number
  scriptType?: string
  method?: string
  error?: string // Error message if processing failed
}

export default function UploadPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [processingResults, setProcessingResults] = useState<ProcessingResult[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [activeTab, setActiveTab] = useState('upload')
  const [savedResults, setSavedResults] = useState<ProcessingResult[]>([]) // Results from database

  // Load saved results from the database
  const loadSavedResults = useCallback(async () => {
    try {
      const response = await fetch('/api/translations?filter=all')
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.translations) {
          // Convert translations to ProcessingResult format
          const results: ProcessingResult[] = data.translations.map((t: any) => ({
            id: t.upload?.id || t.id,
            uploadId: t.upload?.id || t.id,
            status: 'completed' as const,
            progress: 100,
            extractedText: t.originalText,
            translation: t.translatedText,
            confidence: t.confidence,
            scriptType: t.upload?.scriptType || 'Unknown',
            method: 'saved',
            originalName: t.upload?.originalName,
            imageUrl: t.upload?.imageUrl || (t.upload?.id ? `/api/uploads/${t.upload.id}` : undefined),
            // Include inference metadata if available
            coverage: t.upload?.coverage,
            unmapped: t.upload?.unmapped,
            dictionaryVersion: t.upload?.dictionaryVersion,
            glyphs: (t.glyphs || []).map((g: any) => {
              // Use stored confidence, or default to 60% if character is recognized but no meaning
              const hasValidMeaning = g.meaning && 
                                     !g.meaning.includes('Unknown character') && 
                                     !g.meaning.includes('not available') &&
                                     !g.meaning.includes('Character recognized but meaning not available')
              return {
                symbol: g.symbol,
                confidence: g.confidence !== undefined ? g.confidence : (hasValidMeaning ? 0.75 : 0.60),
                position: { x: 0, y: 0, width: 50, height: 50 }, // Default position if not available
                meaning: g.meaning || (g.symbol ? `Character recognized but meaning not available` : 'Unknown'),
                isReconstructed: false
              }
            })
          }))
          setSavedResults(results)
        }
      }
    } catch (error) {
      console.error('Failed to load saved results:', error)
    }
  }, [])

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/login?callbackUrl=/upload')
    } else if (status === 'authenticated') {
      // Load saved results from database when component mounts
      loadSavedResults()
    }
  }, [status, router, loadSavedResults])

  // Error boundary for JSON parsing errors
  useEffect(() => {
    const originalError = console.error
    console.error = (...args) => {
      if (args[0]?.message?.includes('JSON') || args[0]?.message?.includes('Unexpected end')) {
        console.warn('JSON parsing error caught and handled:', args[0])
        return // Suppress the error from crashing the page
      }
      originalError(...args)
    }
    
    return () => {
      console.error = originalError
    }
  }, [])

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Brain className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (!session) {
    return null
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    const newFiles = Array.from(files).map(file => ({
      file,
      preview: URL.createObjectURL(file),
      id: Math.random().toString(36).substr(2, 9)
    }))
    setUploadedFiles(prev => [...prev, ...newFiles])
  }

  const removeFile = (id: string) => {
    setUploadedFiles(prev => {
      const file = prev.find(f => f.id === id)
      if (file) {
        URL.revokeObjectURL(file.preview)
      }
      return prev.filter(f => f.id !== id)
    })
  }

  const processFiles = async () => {
    if (uploadedFiles.length === 0) return

    setIsProcessing(true)
    setActiveTab('processing') // Switch to processing tab
    
    // Initialize processing results
    const results: ProcessingResult[] = uploadedFiles.map(file => ({
      id: file.id,
      status: 'processing' as const,
      progress: 0,
      currentStage: 'tokenization' as const
    }))

    setProcessingResults(results)

    try {
      // Process each file
      for (let i = 0; i < uploadedFiles.length; i++) {
        const file = uploadedFiles[i]
        
        // Step 1: Upload file
        const formData = new FormData()
        formData.append('file', file.file)
        
        // Note: Metadata fields can be added here in the future
        // formData.append('provenance', '...')
        // formData.append('imagingMethod', 'photography')
        // formData.append('scriptType', 'Traditional Chinese')
        
        const uploadResponse = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        })
        
        if (!uploadResponse.ok) {
          // Extract error message from API response
          let errorMessage = 'Upload failed'
          let errorDetails = ''
          try {
            const errorText = await uploadResponse.text()
            if (errorText && errorText.trim() !== '') {
              try {
                const errorData = JSON.parse(errorText)
                errorMessage = errorData.error || errorData.message || 'Upload failed'
                errorDetails = errorData.details || errorData.error || ''
              } catch {
                errorMessage = errorText
                errorDetails = errorText
              }
            }
          } catch {
            errorMessage = 'Failed to upload file'
            errorDetails = 'Unknown error occurred'
          }
          
          // Mark this specific file as failed with error message
          setProcessingResults(prev => 
            prev.map(r => 
              r.id === file.id 
                ? {
                    ...r,
                    status: 'failed',
                    progress: 0,
                    error: errorDetails || errorMessage
                  }
                : r
            )
          )
          
          console.error(`Upload failed for ${file.file.name}:`, errorDetails || errorMessage)
          continue
        }
        
        let uploadData
        try {
          const uploadText = await uploadResponse.text()
          if (!uploadText || uploadText.trim() === '') {
            // Mark as failed
            setProcessingResults(prev => 
              prev.map(r => 
                r.id === file.id 
                  ? {
                      ...r,
                      status: 'failed',
                      progress: 0,
                      error: 'Empty response from upload API'
                    }
                  : r
              )
            )
            continue
          }
          uploadData = JSON.parse(uploadText)
        } catch (parseError: any) {
          console.error('Failed to parse upload response:', parseError)
          // Mark as failed
          setProcessingResults(prev => 
            prev.map(r => 
              r.id === file.id 
                ? {
                    ...r,
                    status: 'failed',
                    progress: 0,
                    error: `Failed to parse upload response: ${parseError.message || 'Unknown parsing error'}`
                  }
                : r
            )
          )
          continue
        }
        
        if (!uploadData.uploadId) {
          // Mark as failed
          setProcessingResults(prev => 
            prev.map(r => 
              r.id === file.id 
                ? {
                    ...r,
                    status: 'failed',
                    progress: 0,
                    error: 'Upload response missing uploadId'
                  }
                : r
            )
          )
          continue
        }
        
        // Update to tokenization stage (OCR extraction)
        setProcessingResults(prev => 
          prev.map(r => 
            r.id === file.id 
              ? {
                  ...r,
                  currentStage: 'tokenization',
                  progress: 10
                }
              : r
          )
        )
        
        // Update progress for tokenization
        setProcessingResults(prev => 
          prev.map(r => 
            r.id === file.id 
              ? {
                  ...r,
                  currentStage: 'tokenization',
                  progress: 30
                }
              : r
          )
        )
        
        // Step 2: Process the uploaded file via external inference service (through our API)
        const processResponse = await fetch('/api/process', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ uploadId: uploadData.uploadId })
        })
        
        // Update to semantic transformer stage (matching & translation)
        setProcessingResults(prev => 
          prev.map(r => 
            r.id === file.id 
              ? {
                  ...r,
                  currentStage: 'semantic',
                  progress: 50
                }
              : r
          )
        )
        
        if (!processResponse.ok) {
          // Extract detailed error message from API response
          let errorMessage = 'Processing failed'
          let errorDetails = ''
          try {
            const errorText = await processResponse.text()
            if (errorText && errorText.trim() !== '') {
              try {
                const errorData = JSON.parse(errorText)
                errorMessage = errorData.error || errorData.message || 'Processing failed'
                errorDetails = errorData.details || errorData.error || ''
              } catch {
                errorMessage = errorText
                errorDetails = errorText
              }
            }
          } catch {
            errorMessage = 'Failed to process image'
            errorDetails = 'Unknown error occurred'
          }
          
          // Mark this specific file as failed with error message
          setProcessingResults(prev => 
            prev.map(r => 
              r.id === file.id 
                ? {
                    ...r,
                    status: 'failed',
                    progress: 0,
                    error: errorDetails || errorMessage
                  }
                : r
            )
          )
          
          // Continue to next file instead of throwing
          console.error(`Processing failed for ${file.file.name}:`, errorDetails || errorMessage)
          continue
        }
        
        let processData
        try {
          const processText = await processResponse.text()
          if (!processText || processText.trim() === '') {
            console.warn('Empty response from process API')
            processData = { success: false, results: null }
          } else {
            processData = JSON.parse(processText)
          }
        } catch (parseError) {
          console.error('Failed to parse process response:', parseError)
          // Mark this file as failed
          setProcessingResults(prev => 
            prev.map(r => 
              r.id === file.id 
                ? {
                    ...r,
                    status: 'failed',
                    progress: 0,
                    error: `Failed to parse processing response: ${parseError instanceof Error ? parseError.message : 'Unknown parsing error'}`
                  }
                : r
            )
          )
          continue
        }
        
        // Update progress for semantic processing
        setProcessingResults(prev => 
          prev.map(r => 
            r.id === file.id 
              ? {
                  ...r,
                  currentStage: 'semantic',
                  progress: 70
                }
              : r
          )
        )
        
        // Step 3: Get detailed results
        const resultsResponse = await fetch(`/api/process?uploadId=${uploadData.uploadId}`)
        if (!resultsResponse.ok) {
          // If results fetch fails, we still have processData, so log but continue
          console.warn(`Failed to fetch detailed results for ${file.file.name}, using process response data`)
        }
        
        // Update to reconstruction stage (if needed) or complete
        setProcessingResults(prev => 
          prev.map(r => 
            r.id === file.id 
              ? {
                  ...r,
                  currentStage: 'reconstruction',
                  progress: 85
                }
              : r
          )
        )
        
        let resultsData
        try {
          const text = await resultsResponse.ok ? await resultsResponse.text() : ''
          if (!text || text.trim() === '') {
            console.warn('Empty response from results API')
            resultsData = { upload: null }
          } else {
            resultsData = JSON.parse(text)
          }
        } catch (parseError) {
          console.error('Failed to parse results response:', parseError)
          // Use processData as fallback - don't mark as failed since we have processData
          resultsData = { upload: null }
        }
        
        // Update progress to complete
        setProcessingResults(prev => {
          const updated = prev.map(r => 
            r.id === file.id 
              ? {
                  ...r,
                  uploadId: uploadData.uploadId, // Store uploadId for exports
                  status: 'completed',
                  progress: 100,
                  currentStage: 'complete',
                  imageUrl: `/api/uploads/${uploadData.uploadId}`, // Add image URL
                  glyphs: (() => {
                    // Try to get glyphs from resultsData first, then fallback to processData
                    if (resultsData.upload?.glyphs && resultsData.upload.glyphs.length > 0) {
                      return resultsData.upload.glyphs.map((g: any) => {
                        // Safely parse boundingBox
                        let position = { x: 0, y: 0, width: 0, height: 0 }
                        try {
                          if (g.boundingBox && typeof g.boundingBox === 'string' && g.boundingBox.trim() !== '') {
                            position = JSON.parse(g.boundingBox)
                          }
                        } catch (e) {
                          console.warn('Failed to parse boundingBox:', e)
                        }
                        const meaning = g.glyph?.description || g.glyph?.name || ''
                        const hasValidMeaning = meaning && 
                                               !meaning.includes('Unknown character') && 
                                               !meaning.includes('Character:') &&
                                               !meaning.includes('not available')
                        return {
                          symbol: g.glyph?.symbol || '',
                          confidence: g.confidence !== undefined ? g.confidence : (hasValidMeaning ? 0.75 : 0.60),
                          position,
                          meaning: meaning || (g.glyph?.symbol ? `Character recognized but meaning not available` : 'Unknown')
                        }
                      })
                    }
                    // Fallback to processData results
                    if (processData.results?.glyphs && processData.results.glyphs.length > 0) {
                      return processData.results.glyphs.map((g: any) => ({
                        symbol: g.symbol || '',
                        confidence: g.confidence || 0,
                        position: { x: 0, y: 0, width: 50, height: 50 },
                        meaning: g.meaning || (g.symbol ? `Unknown character (may need to be added to database)` : 'Unknown')
                      }))
                    }
                    return []
                  })(),
                  extractedText: resultsData.upload?.translations?.[0]?.originalText || 
                                processData.results?.extractedText || 
                                '',
                  translation: resultsData.upload?.translations?.[0]?.translatedText || 
                              processData.results?.translation || 
                              'Translation not available',
                  confidence: resultsData.upload?.translations?.[0]?.confidence || 
                             processData.results?.confidence || 
                             0.90,
                  scriptType: processData.results?.scriptType || 'Unknown',
                  method: processData.results?.method || 'unknown',
                  // Include inference metadata
                  coverage: processData.results?.coverage,
                  unmapped: processData.results?.unmapped,
                  dictionaryVersion: processData.results?.dictionaryVersion
                }
              : r
          )
          
          // Switch to results tab when we have completed results
          const hasCompleted = updated.some(r => r.status === 'completed')
          if (hasCompleted) {
            // Use setTimeout to ensure state is updated first
            setTimeout(() => {
              setActiveTab('results')
            }, 100)
          }
          
          return updated
        })
      }
    } catch (error: any) {
      // This catch should rarely be hit now since we handle errors per-file
      // But if there's an unexpected error, log it and mark remaining files as failed
      console.error('Unexpected processing error:', error)
      const errorMessage = error?.message || error?.toString() || 'An unexpected error occurred'
      
      // Only mark files that are still processing as failed
      setProcessingResults(prev => 
        prev.map(r => 
          r.status === 'processing'
            ? {
                ...r,
                status: 'failed',
                progress: 0,
                error: errorMessage
              }
            : r
        )
      )
    } finally {
      setIsProcessing(false)
      // Tab switching is now handled inside the state update
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      {/* Navigation */}
      <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Home
              </Link>
            </Button>
            <div className="flex items-center space-x-2">
              <Brain className="h-6 w-6 text-primary" />
              <span className="text-lg font-semibold">Rune-X</span>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/translations">
                <History className="mr-2 h-4 w-4" />
                History
              </Link>
            </Button>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl md:text-4xl font-bold mb-4">
              Upload Ancient Texts for Analysis
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Upload images of ancient manuscripts, inscriptions, or seals for AI-powered 
              glyph recognition and semantic translation.
            </p>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="upload">Upload Files</TabsTrigger>
              <TabsTrigger value="processing">Processing</TabsTrigger>
              <TabsTrigger value="results">Results</TabsTrigger>
            </TabsList>

            <TabsContent value="upload" className="mt-8">
              <div className="grid lg:grid-cols-2 gap-8">
                {/* Upload Area */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Upload className="h-5 w-5" />
                      Upload Images
                    </CardTitle>
                    <CardDescription>
                      Click to select files or drag and drop
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="border-2 border-dashed border-primary/20 rounded-lg p-8 text-center">
                      <FileImage className="h-12 w-12 text-primary/40 mx-auto mb-4" />
                      <p className="text-lg font-medium mb-2">
                        Click to upload images
                      </p>
                      <p className="text-sm text-muted-foreground mb-4">
                        Supports JPG, PNG, WebP, TIFF up to 10MB
                      </p>
                      <input
                        type="file"
                        multiple
                        accept="image/*"
                        onChange={handleFileUpload}
                        className="hidden"
                        id="file-upload"
                      />
                      <Button asChild>
                        <label htmlFor="file-upload" className="cursor-pointer">
                          Select Files
                        </label>
                      </Button>
                    </div>

                    {uploadedFiles.length > 0 && (
                      <div className="mt-6">
                        <h4 className="font-medium mb-3">Uploaded Files ({uploadedFiles.length})</h4>
                        <div className="space-y-2">
                          {uploadedFiles.map((file) => (
                            <div
                              key={file.id}
                              className="flex items-center justify-between p-3 bg-muted/30 rounded-lg"
                            >
                              <div className="flex items-center space-x-3">
                                <img
                                  src={file.preview}
                                  alt={file.file.name}
                                  className="w-12 h-12 object-cover rounded"
                                />
                                <div>
                                  <p className="font-medium text-sm">{file.file.name}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {(file.file.size / 1024 / 1024).toFixed(2)} MB
                                  </p>
                                </div>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeFile(file.id)}
                              >
                                Remove
                              </Button>
                            </div>
                          ))}
                        </div>
                        <Button 
                          className="w-full mt-4" 
                          onClick={processFiles}
                          disabled={isProcessing || uploadedFiles.length === 0}
                        >
                          {isProcessing ? 'Processing...' : 'Process Files'}
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Instructions */}
                <Card>
                  <CardHeader>
                    <CardTitle>Guidelines for Best Results</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-start gap-3">
                      <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                      <div>
                        <h4 className="font-medium">Clear Images</h4>
                        <p className="text-sm text-muted-foreground">
                          Use high-resolution images with good lighting and minimal blur
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                      <div>
                        <h4 className="font-medium">Single Script Focus</h4>
                        <p className="text-sm text-muted-foreground">
                          Upload images containing one type of ancient script per file
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                      <div>
                        <h4 className="font-medium">Minimal Background Noise</h4>
                        <p className="text-sm text-muted-foreground">
                          Ensure the text is clearly visible without excessive background elements
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
                      <div>
                        <h4 className="font-medium">Supported Scripts</h4>
                        <p className="text-sm text-muted-foreground">
                          Oracle Bone Script, Bronze Script, Seal Script, Traditional Chinese, 
                          Classical Latin, Ancient Greek
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="processing" className="mt-8">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="h-5 w-5" />
                    AI Processing Status
                  </CardTitle>
                  <CardDescription>
                    Watch as our AI analyzes your ancient texts
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {processingResults.length === 0 ? (
                    <div className="text-center py-12">
                      <Eye className="h-12 w-12 text-muted-foreground/40 mx-auto mb-4" />
                      <p className="text-muted-foreground">
                        No files are currently being processed
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {processingResults.map((result) => {
                        const file = uploadedFiles.find(f => f.id === result.id)
                        return (
                          <div key={result.id} className="space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-3">
                                {file && (
                                  <img
                                    src={file.preview}
                                    alt={file.file.name}
                                    className="w-10 h-10 object-cover rounded"
                                  />
                                )}
                                <div>
                                  <p className="font-medium">{file?.file.name}</p>
                                  <div className="flex items-center gap-2 mt-1">
                                    <Badge variant={
                                      result.status === 'completed' ? 'default' :
                                      result.status === 'processing' ? 'secondary' : 'destructive'
                                    }>
                                      {result.status}
                                    </Badge>
                                    {result.status === 'processing' && result.currentStage && (
                                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                        {result.currentStage === 'tokenization' && (
                                          <>
                                            <Cpu className="h-3.5 w-3.5 text-primary animate-pulse" />
                                            <span>Glyph Tokenization</span>
                                          </>
                                        )}
                                        {result.currentStage === 'semantic' && (
                                          <>
                                            <Network className="h-3.5 w-3.5 text-primary animate-pulse" />
                                            <span>Semantic Transformer</span>
                                          </>
                                        )}
                                        {result.currentStage === 'reconstruction' && (
                                          <>
                                            <Sparkles className="h-3.5 w-3.5 text-primary animate-pulse" />
                                            <span>Generative Reconstruction</span>
                                          </>
                                        )}
                                        {result.currentStage === 'complete' && (
                                          <>
                                            <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                                            <span>Complete</span>
                                          </>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                              <span className="text-sm text-muted-foreground">
                                {result.progress}%
                              </span>
                            </div>
                            <Progress value={result.progress} className="h-2" />
                          </div>
                        )
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="results" className="mt-8">
              <ResultsDisplay 
                processingResults={processingResults}
                savedResults={savedResults}
                uploadedFiles={uploadedFiles}
                onLoadSaved={loadSavedResults}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}