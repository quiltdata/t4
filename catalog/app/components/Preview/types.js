import tagged from 'utils/tagged';


export const PreviewData = tagged([
  'Image', // { handle: object }
  'Markdown', // { rendered: string }
  'Vega', // { spec: Object }
  'Parquet', // { preview: string }
  'Notebook', // { preview: string }
  'Text', // { contents: string, lang: string }
  'Vcf', // { meta: string[], header: string[][], body: string[][] }
  'Table', // { head: string[], tail: string[] }
]);

export const PreviewError = tagged([
  'TooLarge', // { handle }
  'Unsupported', // { handle }
  'DoesNotExist', // { handle }
  'Unexpected', // { handle, originalError: any }
  'MalformedJson', // { handle, originalError: SyntaxError }
]);
