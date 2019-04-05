import tagged from 'utils/tagged';


export const PreviewData = tagged([
  'DataFrame', // { preview: string }
  'Image', // { handle: object }
  'Markdown', // { rendered: string }
  'Notebook', // { preview: string }
  'Table', // { head: string[], tail: string[] }
  'Text', // { contents: string, lang: string }
  'Vcf', // { meta: string[], header: string[][], body: string[][] }
  'Vega', // { spec: Object }
]);

export const PreviewError = tagged([
  'TooLarge', // { handle }
  'Unsupported', // { handle }
  'DoesNotExist', // { handle }
  'Unexpected', // { handle, originalError: any }
  'MalformedJson', // { handle, originalError: SyntaxError }
]);
