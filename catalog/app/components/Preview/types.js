import tagged from 'utils/tagged';


export const PreviewData = tagged([
  'Image', // { url: string }
  'Markdown', // { rendered: string }
  'Vega', // { spec: Object }
  'Parquet', // { preview: string }
  'Notebook', // { preview: string }
  'Text', // { contents: string, lang: string }
]);

export const PreviewError = tagged([
  'TooLarge', // { handle }
  'Unsupported', // { handle }
  'DoesNotExist', // { handle }
  'Unexpected', // { handle, originalError: any }
]);
