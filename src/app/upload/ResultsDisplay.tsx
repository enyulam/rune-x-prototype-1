'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CheckCircle, Download, Share, Eye } from 'lucide-react'

interface ProcessingResult {
  id: string
  uploadId?: string
  status: 'processing' | 'completed' | 'failed'
  progress: number
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
  error?: string
  originalName?: string
  imageUrl?: string
  coverage?: number
  unmapped?: string[]
  dictionaryVersion?: string
}

interface UploadedFile {
  file: File
  preview: string
  id: string
}

interface ResultsDisplayProps {
  processingResults: ProcessingResult[]
  savedResults: ProcessingResult[]
  uploadedFiles: UploadedFile[]
  onLoadSaved: () => void
}

export default function ResultsDisplay({ 
  processingResults, 
  savedResults, 
  uploadedFiles,
  onLoadSaved 
}: ResultsDisplayProps) {
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({})
  const [failedImageLoads, setFailedImageLoads] = useState<Set<string>>(new Set())
  const attemptedLoadsRef = useRef<Set<string>>(new Set())

  // Load saved results when component mounts
  useEffect(() => {
    onLoadSaved()
  }, [onLoadSaved])

  // Get stable list of uploadIds from savedResults
  const savedUploadIds = useMemo(() => {
    return savedResults
      .map(r => r.uploadId)
      .filter((id): id is string => !!id)
      .sort()
      .join(',')
  }, [savedResults])

  // Load images for saved results (only once per uploadId, skip failed ones)
  useEffect(() => {
    // Get list of uploadIds we need to load (haven't attempted yet)
    const uploadIdsToLoad = savedResults
      .map(r => r.uploadId)
      .filter((id): id is string => 
        !!id && 
        !imageUrls[id] && 
        !failedImageLoads.has(id) &&
        !attemptedLoadsRef.current.has(id)
      )
    
    if (uploadIdsToLoad.length === 0) return

    // Mark all as attempted immediately to prevent duplicate requests
    uploadIdsToLoad.forEach(id => attemptedLoadsRef.current.add(id))

    let cancelled = false
    
    const loadImages = async () => {
      const newImageUrls: Record<string, string> = {}
      const newFailedIds = new Set<string>()
      
      // Load images in parallel
      const loadPromises = uploadIdsToLoad.map(async (uploadId) => {
        if (cancelled) return
        
        try {
          const fileResponse = await fetch(`/api/uploads/${uploadId}`)
          if (fileResponse.ok) {
            const blob = await fileResponse.blob()
            if (!cancelled) {
              newImageUrls[uploadId] = URL.createObjectURL(blob)
            }
          } else {
            // Mark as failed - don't retry
            newFailedIds.add(uploadId)
          }
        } catch (error) {
          // Mark as failed - don't retry (silently)
          newFailedIds.add(uploadId)
        }
      })
      
      await Promise.all(loadPromises)
      
      if (cancelled) return
      
      // Update state only if we have changes
      if (Object.keys(newImageUrls).length > 0) {
        setImageUrls(prev => ({ ...prev, ...newImageUrls }))
      }
      if (newFailedIds.size > 0) {
        setFailedImageLoads(prev => new Set([...prev, ...newFailedIds]))
      }
    }

    loadImages()
    
    return () => {
      cancelled = true
    }
  }, [savedUploadIds, imageUrls, failedImageLoads]) // Only re-run when saved uploadIds change

  // Combine and deduplicate results, prefer saved results over processing ones
  const allResults = useMemo(() => {
    const byKey = new Map<string, ProcessingResult>()

    // First, take saved results (from DB)
    for (const r of savedResults) {
      const key = r.uploadId || r.id
      if (!key) continue
      byKey.set(key, r)
    }

    // Then add processing results only if not already present
    for (const r of processingResults) {
      const key = r.uploadId || r.id
      if (!key) continue
      if (byKey.has(key)) continue
      byKey.set(key, r)
    }

    // Only show completed items
    return Array.from(byKey.values()).filter(r => r.status === 'completed')
  }, [processingResults, savedResults])

  if (allResults.length === 0) {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <Eye className="h-12 w-12 text-muted-foreground/40 mx-auto mb-4" />
          <p className="text-muted-foreground">
            No results yet. Upload and process some files to see results here.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-8">
      {allResults.map((result) => {
        // Find file from uploadedFiles or use saved image
        const file = uploadedFiles.find(f => f.id === result.id)
        const imageUrl = file?.preview || result.imageUrl || imageUrls[result.uploadId || ''] || null

        return (
          <Card key={result.uploadId || result.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  Analysis Results
                </CardTitle>
                <div className="flex items-center space-x-2">
                  {result.uploadId && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={async () => {
                        const formats = ['JSON_LD', 'TEI_XML', 'CSV']
                        const selected = window.prompt(
                          `Select export format:\n1. JSON-LD\n2. TEI-XML\n3. CSV\n\nEnter number (1-3):`
                        )
                        if (selected) {
                          const formatIndex = parseInt(selected) - 1
                          if (formatIndex >= 0 && formatIndex < formats.length) {
                            window.open(`/api/export?uploadId=${result.uploadId}&format=${formats[formatIndex]}`, '_blank')
                          }
                        }
                      }}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Export
                    </Button>
                  )}
                  <Button variant="outline" size="sm">
                    <Share className="mr-2 h-4 w-4" />
                    Share
                  </Button>
                </div>
              </div>
              <CardDescription>
                {result.originalName || file?.file.name || 'Processed Image'} • Confidence: {(result.confidence || 0.9) * 100}%
                {result.coverage !== undefined && (
                  <> • Dictionary Coverage: {result.coverage}%</>
                )}
                {result.dictionaryVersion && (
                  <> • Dictionary v{result.dictionaryVersion}</>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Original Image */}
              <div>
                <h4 className="font-medium mb-3">Original Image</h4>
                {imageUrl ? (
                  <img
                    src={imageUrl}
                    alt={result.originalName || 'Processed image'}
                    className="w-full max-w-md mx-auto rounded-lg border"
                    onError={(e) => {
                      // Hide image on error
                      e.currentTarget.style.display = 'none'
                      const parent = e.currentTarget.parentElement
                      if (parent && !parent.querySelector('.image-placeholder')) {
                        const placeholder = document.createElement('div')
                        placeholder.className = 'image-placeholder bg-muted/50 p-8 rounded-lg border text-center text-muted-foreground'
                        placeholder.innerHTML = '<p>Image not available</p>'
                        parent.appendChild(placeholder)
                      }
                    }}
                  />
                ) : (
                  <div className="bg-muted/50 p-8 rounded-lg border text-center text-muted-foreground">
                    <p>Image not available</p>
                    <p className="text-xs mt-2">The original file may have been deleted or moved</p>
                  </div>
                )}
              </div>

              {/* Extracted Text */}
              {result.extractedText && (
                <div>
                  <h4 className="font-medium mb-3">Extracted Text</h4>
                  <div className="bg-muted/50 p-4 rounded-lg border">
                    <p className="text-lg font-mono">{result.extractedText}</p>
                    {result.scriptType && (
                      <div className="mt-2 flex gap-2 text-sm text-muted-foreground">
                        <Badge variant="outline">Script: {result.scriptType}</Badge>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Detected Glyphs */}
              <div>
                <h4 className="font-medium mb-3">
                  Detected Glyphs {result.glyphs && `(${result.glyphs.length})`}
                </h4>
                {result.glyphs && result.glyphs.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {result.glyphs.map((glyph, index) => {
                      const confidence = glyph.confidence || 0
                      const confidencePercent = confidence * 100
                      
                      // Color coding: red for low confidence, green for high confidence
                      // 0-30%: red, 30-70%: yellow/orange, 70-100%: green
                      const getConfidenceColor = (conf: number) => {
                        if (conf === 0) return 'text-red-600' // Unknown characters
                        if (conf < 0.3) return 'text-red-500'
                        if (conf < 0.7) return 'text-yellow-600'
                        return 'text-green-600'
                      }
                      
                      const getConfidenceBgColor = (conf: number) => {
                        if (conf === 0) return 'bg-red-50 border-red-200' // Unknown characters
                        if (conf < 0.3) return 'bg-red-50 border-red-200'
                        if (conf < 0.7) return 'bg-yellow-50 border-yellow-200'
                        return 'bg-green-50 border-green-200'
                      }
                      
                      const isUnknown = confidence === 0 || 
                                        (glyph.meaning && (
                                          glyph.meaning.includes('Unknown character') ||
                                          glyph.meaning.includes('Character recognized but meaning not available')
                                        ))
                      
                      return (
                        <div 
                          key={index} 
                          className={`text-center p-4 border-2 rounded-lg ${getConfidenceBgColor(confidence)}`}
                        >
                          <div className={`text-2xl mb-2 font-bold ${getConfidenceColor(confidence)}`}>
                            {glyph.symbol}
                          </div>
                          <div className="text-sm font-medium mb-1 min-h-[2.5rem]">
                            {glyph.meaning || 'No meaning available'}
                          </div>
                          <div className={`text-xs font-semibold ${getConfidenceColor(confidence)}`}>
                            {confidencePercent.toFixed(1)}% match
                          </div>
                          {glyph.isReconstructed && (
                            <div className="text-xs text-blue-600 mt-1">Reconstructed</div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="bg-muted/50 p-4 rounded-lg border text-center text-muted-foreground">
                    <p>No glyphs detected in this image.</p>
                  </div>
                )}
              </div>

              {/* Translation */}
              {result.translation && (
                <div>
                  <h4 className="font-medium mb-3">Translation & Context</h4>
                  <div className="bg-primary/10 p-4 rounded-lg">
                    <p className="font-medium mb-2">{result.translation}</p>
                    {result.coverage !== undefined && (
                      <div className="mt-3 pt-3 border-t border-primary/20">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">Dictionary Coverage:</span>
                          <Badge variant={result.coverage >= 90 ? "default" : result.coverage >= 70 ? "secondary" : "destructive"}>
                            {result.coverage}%
                          </Badge>
                        </div>
                        {result.unmapped && result.unmapped.length > 0 && (
                          <div className="mt-2 text-sm">
                            <span className="text-muted-foreground">Unmapped characters: </span>
                            <span className="font-mono text-xs bg-muted px-2 py-1 rounded">
                              {result.unmapped.join(', ')}
                            </span>
                          </div>
                        )}
                        {result.dictionaryVersion && (
                          <div className="mt-2 text-xs text-muted-foreground">
                            Dictionary version: {result.dictionaryVersion}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}



