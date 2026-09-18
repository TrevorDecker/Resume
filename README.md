Resume
======

My Resume

A webpage about me can be found at http://trevordecker.github.io/Resume/


To work on this resume setup latex:
    https://tug.org/mactex/mactex-download.html
    https://www.xm1math.net/texmaker/download.html

Generate a PDF:
    python3 generate_pdf.py
    python3 generate_pdf.py --serve

Edit by section:
    preamble.tex              packages, header, footer, macros
    summary.tex               summary
    Employment.tex            jobs
    Education.tex             school, internships, TA / research
    activities.tex            activities
    distinctions.tex          patents, awards
    skills.tex                skills
    Trevor_Decker_Resume.tex  document order only

Unused options are kept as comments at the bottom of each section file,
under `% --- unused / optional ---`.
