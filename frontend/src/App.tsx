import { myAivanEntryUrl } from './lib/myAivan.js';

function App({ myAivanUrl }: { myAivanUrl?: string }) {
  const entryUrl = myAivanEntryUrl(myAivanUrl);

  return (
    <main>
      <h1>abcdYi — Apparel &amp; Textile</h1>
      <p>Start your apparel or textile order in MyAivan, Aivan&apos;s web application.</p>
      <p>Aivan handles inquiry, quotation, and order confirmation. abcdYi handles production, quality control, logistics, and buyer sign-off.</p>
      {entryUrl ? (
        <>
          <p><a href={entryUrl} referrerPolicy="no-referrer">Open MyAivan</a></p>
          <p>Sign in with your MyAivan account. Commercial messages and commitments require human confirmation.</p>
        </>
      ) : (
        <p role="status">MyAivan is not configured. Ask your operator to configure the approved MyAivan web entry URL.</p>
      )}
    </main>
  );
}
export default App;
