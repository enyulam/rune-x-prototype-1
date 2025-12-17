import 'dotenv/config'
import { PrismaClient } from '@prisma/client'
import bcrypt from 'bcryptjs'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Seeding database with ancient scripts and glyphs...')

  // Create ancient scripts
  const scripts = [
    {
      name: 'Oracle Bone Script',
      description: 'Earliest known Chinese writing system, used for divination during the Shang Dynasty',
      region: 'China',
      timePeriod: '1600-1046 BCE'
    },
    {
      name: 'Bronze Script',
      description: 'Chinese writing characters inscribed on bronze artifacts during the Shang and Zhou Dynasties',
      region: 'China',
      timePeriod: '1600-256 BCE'
    },
    {
      name: 'Seal Script',
      description: 'Ancient Chinese script used for formal seals and ceremonial inscriptions',
      region: 'China',
      timePeriod: '770-256 BCE'
    },
    {
      name: 'Traditional Chinese',
      description: 'Traditional Chinese characters used throughout Chinese history',
      region: 'China',
      timePeriod: '206 BCE - Present'
    },
    {
      name: 'Classical Latin',
      description: 'Classical Latin alphabet and writing system of ancient Rome',
      region: 'Roman Empire',
      timePeriod: '753 BCE - 476 CE'
    },
    {
      name: 'Ancient Greek',
      description: 'Ancient Greek alphabet and writing system',
      region: 'Greece',
      timePeriod: '800 BCE - 300 CE'
    }
  ]

  for (const scriptData of scripts) {
    await prisma.ancientScript.upsert({
      where: { name: scriptData.name },
      update: scriptData,
      create: scriptData
    })
  }

  console.log('✅ Ancient scripts created')

  // Get the created scripts
  const oracleScript = await prisma.ancientScript.findUnique({ where: { name: 'Oracle Bone Script' } })
  const bronzeScript = await prisma.ancientScript.findUnique({ where: { name: 'Bronze Script' } })
  const sealScript = await prisma.ancientScript.findUnique({ where: { name: 'Seal Script' } })
  const traditionalScript = await prisma.ancientScript.findUnique({ where: { name: 'Traditional Chinese' } })

  // Create glyphs for Traditional Chinese
  const chineseGlyphs = [
    { symbol: '道', name: 'Dao', description: 'The way, path, or principle; fundamental concept in Chinese philosophy', strokeCount: 12, confidence: 0.95 },
    { symbol: '法', name: 'Fa', description: 'Law, method, or principle', strokeCount: 8, confidence: 0.88 },
    { symbol: '自', name: 'Zi', description: 'Self, from, or natural', strokeCount: 6, confidence: 0.92 },
    { symbol: '然', name: 'Ran', description: 'Thus, so, or natural state', strokeCount: 12, confidence: 0.85 },
    { symbol: '人', name: 'Ren', description: 'Person, human being', strokeCount: 2, confidence: 0.98 },
    { symbol: '天', name: 'Tian', description: 'Heaven, sky, or nature', strokeCount: 4, confidence: 0.93 },
    { symbol: '地', name: 'Di', description: 'Earth, ground, or place', strokeCount: 6, confidence: 0.87 },
    { symbol: '德', name: 'De', description: 'Virtue, morality, or character', strokeCount: 15, confidence: 0.89 },
    { symbol: '仁', name: 'Ren', description: 'Benevolence, humanity, kindness', strokeCount: 4, confidence: 0.91 },
    { symbol: '义', name: 'Yi', description: 'Righteousness, justice, duty', strokeCount: 13, confidence: 0.86 },
    { symbol: '礼', name: 'Li', description: 'Ritual, propriety, ceremony', strokeCount: 5, confidence: 0.84 },
    { symbol: '智', name: 'Zhi', description: 'Wisdom, intelligence, knowledge', strokeCount: 12, confidence: 0.90 }
  ]

  if (traditionalScript) {
    for (const glyphData of chineseGlyphs) {
      const existingGlyph = await prisma.glyph.findFirst({
        where: { 
          symbol: glyphData.symbol,
          scriptId: traditionalScript.id
        }
      })
      
      if (!existingGlyph) {
        await prisma.glyph.create({
          data: {
            ...glyphData,
            scriptId: traditionalScript.id
          }
        })
      }
    }
  }

  // Create glyphs for Oracle Bone Script
  const oracleGlyphs = [
    { symbol: '𠔼', name: 'Early Dao', description: 'Oracle bone form of Dao character', strokeCount: 8, confidence: 0.75 },
    { symbol: '𡆧', name: 'Early Ren', description: 'Oracle bone form of Ren (person)', strokeCount: 3, confidence: 0.82 },
    { symbol: '𠀆', name: 'Early Tian', description: 'Oracle bone form of Tian (heaven)', strokeCount: 6, confidence: 0.78 }
  ]

  if (oracleScript) {
    for (const glyphData of oracleGlyphs) {
      const existingGlyph = await prisma.glyph.findFirst({
        where: { 
          symbol: glyphData.symbol,
          scriptId: oracleScript.id
        }
      })
      
      if (!existingGlyph) {
        await prisma.glyph.create({
          data: {
            ...glyphData,
            scriptId: oracleScript.id
          }
        })
      }
    }
  }

  console.log('✅ Glyphs created')

  // Create a demo user
  const hashedPassword = await bcrypt.hash('demo123', 10)
  const demoUser = await prisma.user.upsert({
    where: { email: 'demo@projectdecypher.com' },
    update: {},
    create: {
      email: 'demo@projectdecypher.com',
      name: 'Demo User',
      password: hashedPassword,
      role: 'USER'
    }
  })

  console.log('✅ Demo user created')

  // Create a demo upload for translations
  const demoUpload = await prisma.upload.create({
    data: {
      userId: demoUser.id,
      originalName: 'demo_ancient_text.jpg',
      filePath: '/demo/demo_ancient_text.jpg',
      status: 'COMPLETED',
      processedAt: new Date()
    }
  })

  console.log('✅ Demo upload created')

  // Create some sample translations
  const sampleTranslations = [
    {
      uploadId: demoUpload.id,
      originalText: '道法自然',
      translatedText: 'The Tao follows nature - A fundamental concept in Taoist philosophy suggesting that the natural way of things is the best way.',
      confidence: 0.92,
      language: 'English',
      context: 'Taoist philosophy, Laozi'
    },
    {
      uploadId: demoUpload.id,
      originalText: '天人合一',
      translatedText: 'Heaven and humanity are one - The unity between the cosmos and human existence.',
      confidence: 0.88,
      language: 'English',
      context: 'Chinese philosophy, harmony between human and nature'
    },
    {
      uploadId: demoUpload.id,
      originalText: '仁义礼智',
      translatedText: 'Benevolence, righteousness, propriety, and wisdom - The four cardinal virtues in Confucianism.',
      confidence: 0.90,
      language: 'English',
      context: 'Confucian philosophy, moral cultivation'
    }
  ]

  for (const translationData of sampleTranslations) {
    await prisma.translation.create({
      data: translationData
    })
  }

  console.log('✅ Sample translations created')
  console.log('🎉 Database seeding completed!')
}

main()
  .catch((e) => {
    console.error('❌ Error seeding database:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })