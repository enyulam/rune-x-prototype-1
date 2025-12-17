'use client'

import { useState } from 'react'
import { useSession, signOut } from 'next-auth/react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Brain, 
  Upload, 
  History, 
  Globe, 
  Zap, 
  Users, 
  BookOpen, 
  Cpu,
  ArrowRight,
  CheckCircle,
  BarChart3,
  Eye,
  Sparkles,
  LogIn,
  User,
  LogOut
} from 'lucide-react'

export default function Home() {
  const [activeDemo, setActiveDemo] = useState('upload')
  const { data: session, status } = useSession()

  return (
    <div id="top" className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      {/* Navigation */}
      <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Brain className="h-8 w-8 text-primary" />
            <span className="text-xl font-bold">Rune-X</span>
          </div>
          <div className="flex items-center space-x-4">
            <Button variant="ghost" asChild>
              <Link href="#features">Features</Link>
            </Button>
            <Button variant="ghost" asChild>
              <Link href="#demo">Demo</Link>
            </Button>
            {session && (
              <Button variant="ghost" asChild>
                <Link href="/translations">Translations</Link>
              </Button>
            )}
            {session && (
              <Button variant="ghost" asChild>
                <Link href="/dashboard">
                  <User className="mr-2 h-4 w-4" />
                  Dashboard
                </Link>
              </Button>
            )}
            {session ? (
              <Button variant="outline" onClick={() => signOut({ callbackUrl: '/' })}>
                <LogOut className="mr-2 h-4 w-4" />
                Sign Out
              </Button>
            ) : (
              <>
                <Button variant="ghost" asChild>
                  <Link href="/auth/login">
                    <LogIn className="mr-2 h-4 w-4" />
                    Sign In
                  </Link>
                </Button>
                <Button asChild>
                  <Link href="/auth/register">Get Started</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-14 md:py-16">
        <div className="max-w-4xl mx-auto text-center">
          <Badge className="mb-4" variant="secondary">
            <Sparkles className="w-3 h-3 mr-1" />
            AI-Powered Cultural Intelligence
          </Badge>
          <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Rune-X
          </h1>
          <p className="text-xl text-muted-foreground mb-8 leading-relaxed">
            Interpreting the Past. Empowering the Future. Our advanced multimodal AI platform 
            transforms digitised inscriptions into structured, machine-readable knowledge through 
            glyph tokenisation, semantic inference, and generative reconstruction.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {session ? (
              <Button size="lg" className="text-lg px-8" asChild>
                <Link href="/upload">
                  <Upload className="mr-2 h-5 w-5" />
                  Upload Text
                </Link>
              </Button>
            ) : (
              <Button size="lg" className="text-lg px-8" asChild>
                <Link href="/auth/register">
                  <Upload className="mr-2 h-5 w-5" />
                  Get Started
                </Link>
              </Button>
            )}
            <Button size="lg" variant="outline" className="text-lg px-8" asChild>
              <Link href="#demo">
                <Eye className="mr-2 h-5 w-5" />
                Watch Demo
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-muted/40 mx-4" />

      {/* Features Section */}
      <section id="features" className="py-14 md:py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Core Features</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Cutting-edge technology that bridges ancient wisdom with modern AI
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <Card className="relative overflow-hidden group hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <Cpu className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Advanced Glyph Tokenization</CardTitle>
                <CardDescription>
                  Converts ancient texts into structured glyph tokens, capturing stroke patterns, 
                  radicals, and stylistic nuances across different historical periods.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="relative overflow-hidden group hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <Brain className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Transformer-Based Architecture</CardTitle>
                <CardDescription>
                  Maps recognized tokens to probable semantic meanings through cross-language 
                  pattern analysis and continuous learning.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="relative overflow-hidden group hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <Zap className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Real-time Processing</CardTitle>
                <CardDescription>
                  Upload manuscripts or seal images and receive AI-assisted translations 
                  and reconstructions instantly.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="relative overflow-hidden group hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <Globe className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Multi-Language Support</CardTitle>
                <CardDescription>
                  Supports Traditional Chinese, Latin, Greek, and other ancient scripts 
                  with culturally accurate interpretations.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="relative overflow-hidden group hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <Users className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Collaborative Learning</CardTitle>
                <CardDescription>
                  System improves through user feedback and expert validation, 
                  ensuring continuous accuracy enhancement.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="relative overflow-hidden group hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                  <BookOpen className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Academic Integration</CardTitle>
                <CardDescription>
                  Designed for researchers, educators, and cultural institutions 
                  with export capabilities for academic use.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* Demo Section */}
      <section id="demo" className="py-20 bg-primary/5">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">See It In Action</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Experience the power of AI-driven ancient text decryption
            </p>
          </div>

          <div className="max-w-4xl mx-auto">
            <Tabs value={activeDemo} onValueChange={setActiveDemo} className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="upload">Upload & Process</TabsTrigger>
                <TabsTrigger value="analyze">Glyph Analysis</TabsTrigger>
                <TabsTrigger value="translate">Translation</TabsTrigger>
              </TabsList>
              
              <TabsContent value="upload" className="mt-8">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Upload className="h-5 w-5" />
                      Step 1: Upload Your Ancient Text
                    </CardTitle>
                    <CardDescription>
                      Simply upload an image of any ancient manuscript, inscription, or seal
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="border-2 border-dashed border-primary/20 rounded-lg p-8 text-center">
                      <Upload className="h-12 w-12 text-primary/40 mx-auto mb-4" />
                      <p className="text-lg font-medium mb-2">Drop your image here</p>
                      <p className="text-sm text-muted-foreground mb-4">
                        Supports JPG, PNG, WebP formats up to 10MB
                      </p>
                      <Button>Select File</Button>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="analyze" className="mt-8">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Eye className="h-5 w-5" />
                      Step 2: AI-Powered Glyph Recognition
                    </CardTitle>
                    <CardDescription>
                      Our AI identifies and tokenizes each symbol with confidence scores
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {['甲骨文', '金文', '篆书', '隶书'].map((script, index) => (
                        <div key={script} className="text-center p-4 border rounded-lg">
                          <div className="text-2xl mb-2">📜</div>
                          <div className="font-medium">{script}</div>
                          <div className="text-sm text-green-600">95% match</div>
                        </div>
                      ))}
                    </div>
                    <div className="bg-muted/50 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">Processing Progress</span>
                        <span className="text-sm text-muted-foreground">12 symbols found</span>
                      </div>
                      <div className="w-full bg-background rounded-full h-2">
                        <div className="bg-primary h-2 rounded-full" style={{width: '75%'}}></div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="translate" className="mt-8">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BookOpen className="h-5 w-5" />
                      Step 3: Semantic Translation & Context
                    </CardTitle>
                    <CardDescription>
                      Get comprehensive translations with historical context
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid md:grid-cols-2 gap-6">
                      <div>
                        <h4 className="font-medium mb-2">Original Text</h4>
                        <div className="bg-muted/30 p-4 rounded-lg text-center">
                          <div className="text-3xl mb-2">道法自然</div>
                          <div className="text-sm text-muted-foreground">Ancient Chinese</div>
                        </div>
                      </div>
                      <div>
                        <h4 className="font-medium mb-2">Translation</h4>
                        <div className="bg-primary/10 p-4 rounded-lg">
                          <div className="font-medium mb-2">"The Tao follows nature"</div>
                          <div className="text-sm text-muted-foreground">
                            A fundamental concept in Taoist philosophy suggesting that 
                            the natural way of things is the best way.
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="h-4 w-4" />
                      <span>Translation confidence: 92%</span>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold mb-6">
                Why Rune-X?
              </h2>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-6 w-6 text-green-500 mt-0.5" />
                  <div>
                    <h3 className="font-semibold">Preserve Cultural Heritage</h3>
                    <p className="text-muted-foreground">
                      Digitize and protect ancient texts before they're lost to time
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-6 w-6 text-green-500 mt-0.5" />
                  <div>
                    <h3 className="font-semibold">Accelerate Research</h3>
                    <p className="text-muted-foreground">
                      Reduce decoding time from months to minutes with AI assistance
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-6 w-6 text-green-500 mt-0.5" />
                  <div>
                    <h3 className="font-semibold">Democratize Access</h3>
                    <p className="text-muted-foreground">
                      Make ancient knowledge accessible to everyone, not just specialists
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-6 w-6 text-green-500 mt-0.5" />
                  <div>
                    <h3 className="font-semibold">Continuous Learning</h3>
                    <p className="text-muted-foreground">
                      System improves with each use, building collective knowledge
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="relative">
              <div className="aspect-square rounded-2xl overflow-hidden shadow-md border bg-muted/30">
                <img
                  src="https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=1200&q=80"
                  alt="Ancient manuscript imagery"
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary text-primary-foreground">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to Unlock Ancient Wisdom?
          </h2>
          <p className="text-xl mb-8 opacity-90 max-w-2xl mx-auto">
            Join us in revolutionizing how humanity preserves and understands its written heritage
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" variant="secondary" className="text-lg px-8" asChild>
              <Link href="/upload">
                Start Deciphering
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button
              size="lg"
              variant="secondary"
              className="text-lg px-8 bg-white text-primary hover:bg-white/90"
              asChild
            >
              <Link href="#top">Back to Top</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <Brain className="h-6 w-6 text-primary" />
              <span className="font-semibold">Rune-X</span>
            </div>
            <div className="text-sm text-muted-foreground">
              © 2025 Zhicong Technology. Interpreting the past. Empowering the future.
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}