# Public IndexNow verification match

Reviewed on 5 November 2026 against source commit
`8f9937167c23c71379409be7bef1978a43595f1f` and its reachable history.
Gitleaks 8.30.1 reported two `generic-api-key` findings in the current source
snapshot and two in reachable history. All four refer to the exact
`indexNowKey` declaration whose public verification filename is recorded below.

The declaration in `scripts/build-domain.mjs` supplies the contents and filename
of the generated static verification file
`242a5dcf79d9b1321ecc7abbcc603171.txt`. The declaration in
`scripts/check-domain.mjs` verifies that this file contains the same value.
The same declarations and public-file write are present in their introducing
commit, `2d5461331a6bf752409e11f3a487700a363bd072`. Neither source value nor
published-file content is changed by this adjudication.

This is a public site-ownership verification value used by IndexNow. Its protocol
requires the key file to be available without login so participating search
engines can verify the host. The value can authorize IndexNow notifications for
that host; this review does not classify arbitrary API keys as public or claim
that the value has no protocol authority. It is deliberately part of this
project's public static export. No notifications were sent as part of this
review.

The public HTTPS verification endpoint was also retrieved without credentials
on 5 November 2026 and returned exactly the declared value plus a newline.
This establishes intentional public deployment, as well as the source-level
export contract. The review did not submit URLs or rotate the verification key.

The rule-specific allowlist requires both one of the two exact source paths
and the entire detected field/value pair with start and end anchors. The only
absolute-path prefix accepted is the existing scanner's temporary source-copy
directory. It preserves the exact field name, single quotes,
spelling, case, value and lack of whitespace around the equals sign. It applies
only to `generic-api-key`. It does not exempt whole paths, commits, whole lines,
arbitrary verification values, provider-specific rules or other credentials on
the same line. All upstream rules, the full reachable-history scan and the
tracked/nonignored source-snapshot scan remain enabled.

The real scanner controls cover the standalone declaration and the existing
minified validation line, then require continued detection of a changed value,
the public value in a credential field, prefixed and suffixed field names, an
appended value, unrelated credentials before and after it on the same line,
changed field case, changed quotes, changed whitespace, an identical declaration
in a different or nested path, and a provider-specific token format. Synthetic
control credentials were generated for validation and
were never live credentials. Reports redact matched values.

Reassess or remove this exact exception if the verification value, its use, its
public-file output or the detected declaration changes. A rotated or different
value deliberately fails this exact exception and requires a new review.

References: [IndexNow's public verification-file instructions](https://www.indexnow.org/faq#api-key-and-verification),
[the introducing build source](https://github.com/mohammadrezwankhan/zephyrtrade/blob/2d5461331a6bf752409e11f3a487700a363bd072/scripts/build-domain.mjs),
[Gitleaks 8.30.1 rule-specific allowlist configuration](https://github.com/gitleaks/gitleaks/blob/v8.30.1/README.md#configuration).
