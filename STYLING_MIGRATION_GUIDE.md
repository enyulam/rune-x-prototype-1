# Styling Migration Guide: Match Rune-X Prototype Look 1:1

This guide provides **exact diffs** to transform your other project's styling to match the Rune-X Prototype platform.

---

## Step 1: Install Required Dependencies

In your **other project's root**, run:

```bash
npm install tailwindcss@^4 @tailwindcss/postcss@^4 tailwindcss-animate \
  class-variance-authority clsx tailwind-merge \
  lucide-react \
  @radix-ui/react-accordion @radix-ui/react-alert-dialog @radix-ui/react-aspect-ratio \
  @radix-ui/react-avatar @radix-ui/react-checkbox @radix-ui/react-collapsible \
  @radix-ui/react-context-menu @radix-ui/react-dialog @radix-ui/react-dropdown-menu \
  @radix-ui/react-hover-card @radix-ui/react-label @radix-ui/react-menubar \
  @radix-ui/react-navigation-menu @radix-ui/react-popover @radix-ui/react-progress \
  @radix-ui/react-radio-group @radix-ui/react-scroll-area @radix-ui/react-select \
  @radix-ui/react-separator @radix-ui/react-switch @radix-ui/react-tabs \
  @radix-ui/react-toast @radix-ui/react-tooltip
```

**Remove** `react-hot-toast` (we'll replace it with shadcn/ui's Toaster):

```bash
npm uninstall react-hot-toast
```

---

## Step 2: Update `postcss.config.mjs`

**Replace** your existing `postcss.config.mjs` (or create it if missing) with:

```javascript
const config = {
  plugins: ["@tailwindcss/postcss"],
};

export default config;
```

**Note:** If you have a `postcss.config.js` file, delete it and use `.mjs` instead.

---

## Step 3: Replace `tailwind.config.ts`

**Replace** your entire `tailwind.config.ts` with:

```typescript
import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
    darkMode: "class",
    content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
  	extend: {
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		}
  	}
  },
  plugins: [tailwindcssAnimate],
};
export default config;
```

**Key changes:**
- Added `darkMode: "class"`
- Replaced custom colors with CSS variable-based system
- Added `tailwindcssAnimate` plugin
- Updated content paths to include `./pages/**` and `./components/**`

---

## Step 4: Replace `app/globals.css` (or `src/app/globals.css`)

**Replace** your entire `globals.css` file with:

```css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
  --color-sidebar-ring: var(--sidebar-ring);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar: var(--sidebar);
  --color-chart-5: var(--chart-5);
  --color-chart-4: var(--chart-4);
  --color-chart-3: var(--chart-3);
  --color-chart-2: var(--chart-2);
  --color-chart-1: var(--chart-1);
  --color-ring: var(--ring);
  --color-input: var(--input);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-accent-foreground: var(--accent-foreground);
  --color-accent: var(--accent);
  --color-muted-foreground: var(--muted-foreground);
  --color-muted: var(--muted);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-secondary: var(--secondary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary: var(--primary);
  --color-popover-foreground: var(--popover-foreground);
  --color-popover: var(--popover);
  --color-card-foreground: var(--card-foreground);
  --color-card: var(--card);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}

:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
  --chart-1: oklch(0.646 0.222 41.116);
  --chart-2: oklch(0.6 0.118 184.704);
  --chart-3: oklch(0.398 0.07 227.392);
  --chart-4: oklch(0.828 0.189 84.429);
  --chart-5: oklch(0.769 0.188 70.08);
  --sidebar: oklch(0.985 0 0);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: oklch(0.205 0 0);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.97 0 0);
  --sidebar-accent-foreground: oklch(0.205 0 0);
  --sidebar-border: oklch(0.922 0 0);
  --sidebar-ring: oklch(0.708 0 0);
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --card: oklch(0.205 0 0);
  --card-foreground: oklch(0.985 0 0);
  --popover: oklch(0.205 0 0);
  --popover-foreground: oklch(0.985 0 0);
  --primary: oklch(0.922 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --secondary: oklch(0.269 0 0);
  --secondary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.269 0 0);
  --muted-foreground: oklch(0.708 0 0);
  --accent: oklch(0.269 0 0);
  --accent-foreground: oklch(0.985 0 0);
  --destructive: oklch(0.704 0.191 22.216);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(0.556 0 0);
  --chart-1: oklch(0.488 0.243 264.376);
  --chart-2: oklch(0.696 0.17 162.48);
  --chart-3: oklch(0.769 0.188 70.08);
  --chart-4: oklch(0.627 0.265 303.9);
  --chart-5: oklch(0.645 0.246 16.439);
  --sidebar: oklch(0.205 0 0);
  --sidebar-foreground: oklch(0.985 0 0);
  --sidebar-primary: oklch(0.488 0.243 264.376);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.269 0 0);
  --sidebar-accent-foreground: oklch(0.985 0 0);
  --sidebar-border: oklch(1 0 0 / 10%);
  --sidebar-ring: oklch(0.556 0 0);
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

**Key changes:**
- Uses Tailwind CSS v4 syntax (`@import "tailwindcss"`)
- Defines CSS variables for theming (light/dark mode)
- Uses OKLCH color space for better color consistency

---

## Step 5: Update `app/layout.tsx` (or `src/app/layout.tsx`)

**Replace** your entire `layout.tsx` with:

```typescript
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Rune-X · Chinese OCR & Translation",
  description: "Extract Chinese text from images with OCR, character meanings, and translations",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}
```

**Key changes:**
- Removed `react-hot-toast` import and `<Toaster>` from `react-hot-toast`
- Added `import { Toaster } from "@/components/ui/toaster"` (shadcn/ui)
- Added `suppressHydrationWarning` to `<html>` tag (for dark mode support)
- Added `bg-background text-foreground` classes to `<body>`
- Removed custom toast styling (handled by shadcn/ui now)

---

## Step 6: Copy UI Components and Utilities

### 6a. Copy `src/lib/utils.ts`

Create `lib/utils.ts` (or `src/lib/utils.ts` depending on your structure):

```typescript
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

### 6b. Copy All UI Components

From **Rune-X Prototype**, copy the entire `src/components/ui` folder to your other project:

**Source:** `Rune X (Prototype)/src/components/ui/`  
**Target:** `your-other-frontend/components/ui/` (or `src/components/ui/` if you use `src/`)

**Required components for basic functionality:**
- `button.tsx`
- `card.tsx`
- `input.tsx`
- `label.tsx`
- `toaster.tsx`
- `toast.tsx`
- `table.tsx`
- `badge.tsx`

**Optional but recommended:**
- `dialog.tsx`
- `dropdown-menu.tsx`
- `select.tsx`
- `separator.tsx`
- `tabs.tsx`
- `progress.tsx`

---

## Step 7: Update Your Pages to Use New Components

### Example: Update Upload Page

**Before (using custom components):**
```tsx
import { PrimaryButton } from "@/components/PrimaryButton";
import { Card } from "@/components/Card";

export default function UploadPage() {
  return (
    <Card>
      <PrimaryButton>Upload</PrimaryButton>
    </Card>
  );
}
```

**After (using shadcn/ui components):**
```tsx
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function UploadPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Image</CardTitle>
      </CardHeader>
      <CardContent>
        <Button>Upload</Button>
      </CardContent>
    </Card>
  );
}
```

### Example: Replace react-hot-toast with shadcn/ui Toast

**Before:**
```tsx
import toast from "react-hot-toast";

function handleUpload() {
  toast.success("Upload successful!");
  // or
  toast.error("Upload failed!");
}
```

**After:**
```tsx
import { toast } from "@/components/ui/use-toast";

function handleUpload() {
  toast({
    title: "Success",
    description: "Upload successful!",
  });
  // or
  toast({
    variant: "destructive",
    title: "Error",
    description: "Upload failed!",
  });
}
```

---

## Step 8: Verify Path Aliases

Ensure your `tsconfig.json` has the correct path aliases:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

**Or if you don't use `src/` folder:**
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

---

## Step 9: Test the Migration

1. **Start your dev server:**
   ```bash
   npm run dev
   ```

2. **Check for errors:**
   - Missing imports → Install missing packages
   - Type errors → Check path aliases in `tsconfig.json`
   - Styling issues → Verify `globals.css` is imported in `layout.tsx`

3. **Visual verification:**
   - Colors should match the Rune-X Prototype (neutral grays, proper contrast)
   - Buttons should have rounded corners and proper hover states
   - Cards should have subtle shadows and borders
   - Dark mode should work (add `class="dark"` to `<html>` to test)

---

## Step 10: Optional - Add Dark Mode Toggle

If you want dark mode support, create a theme toggle component:

```tsx
// components/theme-toggle.tsx
"use client";

import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
```

Then install `next-themes`:
```bash
npm install next-themes
```

And wrap your layout with a ThemeProvider (if you want dark mode).

---

## Summary of Changes

✅ **Dependencies:** Added Tailwind v4, shadcn/ui components, Radix UI primitives  
✅ **Config:** Replaced Tailwind config with CSS variable-based system  
✅ **Styles:** Replaced globals.css with Tailwind v4 + OKLCH color system  
✅ **Layout:** Swapped react-hot-toast for shadcn/ui Toaster  
✅ **Components:** Copied all UI components from Rune-X Prototype  
✅ **Utilities:** Added `cn()` utility for className merging  

Your other project should now have **identical styling** to the Rune-X Prototype! 🎨


