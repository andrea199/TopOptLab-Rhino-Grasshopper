"""Shared funding acknowledgement for the README and offline English manual."""
import html
import os
import re

PROJECT_URL = "https://cordis.europa.eu/project/id/101161052"
PROJECT_NAME = "ARCHIBIOFOAM"
GRANT = "101161052"
ACKNOWLEDGEMENT = (
    "The authors acknowledge support from the ARCHIBIOFOAM project, "
    "which received funding from the European Union’s Horizon Europe research "
    "and innovation programme under grant agreement No 101161052."
)
DISCLAIMER = (
    "Views and opinions expressed are however those of the author(s) only "
    "and do not necessarily reflect those of the European Union or European "
    "Innovation Council and SMEs Executive Agency (EISMEA). Neither the "
    "European Union nor the granting authority can be held responsible for them."
)
IMAGE = "assets/funding/eic-funded-by-eu.png"
START = "<!-- FUNDING ACKNOWLEDGEMENT START -->"
END = "<!-- FUNDING ACKNOWLEDGEMENT END -->"


def funding_html(page, site):
    def relative(target):
        return os.path.relpath(site / target, page.parent).replace("\\", "/")

    emblem = ('<a href="' + PROJECT_URL + '"><img src="' + relative(IMAGE)
              + '" width="253" height="41" alt="European Innovation Council. '
              'Funded by the European Union."></a>')
    if page == site / "index.html":
        content = ('<section class="manual-funding" id="acknowledgements">'
                   '<h2>Funding acknowledgements</h2>' + emblem
                   + '<p>' + html.escape(ACKNOWLEDGEMENT) + '</p><p>'
                   + html.escape(DISCLAIMER) + '</p><p><a href="' + PROJECT_URL
                   + '">ARCHIBIOFOAM — project and grant information</a></p></section>')
    else:
        content = ('<footer class="manual-funding">' + emblem
                   + '<p>ARCHIBIOFOAM · Horizon Europe · Grant agreement No '
                   + GRANT + '. <a href="' + relative("index.html")
                   + '#acknowledgements">Funding acknowledgements and disclaimer</a>.'
                   '</p></footer>')
    return START + content + END


def update_readme(repo):
    path = repo / "README.md"
    text = path.read_text(encoding="utf-8")
    block = (START + "\n## Funding acknowledgements\n\n"
             + '[![European Innovation Council. Funded by the European Union.]('
             + 'docs/manual/' + IMAGE + ')](' + PROJECT_URL + ')\n\n'
             + ACKNOWLEDGEMENT + "\n\n" + DISCLAIMER + "\n\n"
             + '[ARCHIBIOFOAM — project and grant information](' + PROJECT_URL
             + ").\n" + END)
    if START in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END),
                      lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf-8")
