import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

const shades = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]

/**
 * PrimeVue's Aura theme, made monochrome: near-black primary buttons and neutral grays, so color is
 * left for meaning (money in and out, negative balances, errors).
 */
export const LedgerTheme = definePreset(Aura, {
  semantic: {
    primary: Object.fromEntries(shades.map((shade) => [shade, `{zinc.${shade}}`])),
    colorScheme: {
      light: {
        primary: {
          color: '{zinc.900}',
          contrastColor: '#ffffff',
          hoverColor: '{zinc.700}',
          activeColor: '{zinc.800}',
        },
        highlight: {
          background: '{zinc.100}',
          focusBackground: '{zinc.200}',
          color: '{zinc.900}',
          focusColor: '{zinc.900}',
        },
        surface: Object.fromEntries([['0', '#ffffff'], ...shades.map((shade) => [shade, `{zinc.${shade}}`])]),
        // Near-black text with a mid-gray for secondary details (Aura's default text is a softer gray).
        text: {
          color: '{zinc.900}',
          hoverColor: '{zinc.950}',
          mutedColor: '{zinc.500}',
          hoverMutedColor: '{zinc.600}',
        },
      },
    },
  },
})
