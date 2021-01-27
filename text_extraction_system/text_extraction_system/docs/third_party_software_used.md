# Third-party Software Used in the Project
This document is for tracking the third-party software used in the project and its licenses.

## LibreOffice
https://www.libreoffice.org/

## Description
Free office suite. Used for converting ("printing") popular document types to PDF.

### Developer
[The Document Foundation](https://www.documentfoundation.org/)

### License
[Mozilla Public License v2.0](mlpv2.txt)

### Usage Notes
https://www.mozilla.org/en-US/MPL/2.0/FAQ/

Q7: I want to distribute (outside my organization) complete and unchanged executable programs built from MPL-licensed software by someone other than me. What do I have to do?

As long as the people who distributed the program to you have complied with the MPL, typically nothing. To check and see if the people who distributed the program to you have complied with the MPL, look for the notice that tells you where the software is available in Source Code form (i.e., check that it complies with Section 3.2(a)), and then check that the Source Code is available in that place, including a notice that informs you that the Source Code is available under the terms of the MPL (i.e., check that it complies with Section 3.1).

If you are only distributing libraries, or are only distributing some parts of the program as you received it, it could be that you need to take extra steps to make sure that users of your program are appropriately informed of their rights, as required by section 3.2(a).

In the case of Mozilla Firefox, the Mozilla-provided executable programs already meet the requirements of Section 3, including the notices required by Section 3.1 and 3.2.

If you want to add your own terms when you distribute the software, Section 3.2(b) requires that those terms must not restrict a recipient's rights under the MPL, and if you offer a warranty on the software, Section 3.5 requires you to make clear that it is offered by you alone.

## Apache PDFBox
https://pdfbox.apache.org/

### Description
The Apache PDFBox® library is an open source Java tool for working with PDF documents.

### Developer
Apache Software Foundation

### License
[Apache License 2.0](apache20.txt)


## Apache TIKA
https://tika.apache.org

### Description
The Apache Tika™ toolkit detects and extracts metadata and text from over a thousand different file types (such as PPT, XLS, and PDF).

### Developer
Apache Software Foundation

### License
[Apache License 2.0](apache20.txt)

### Usage Notes
Text Extraction System does not use TIKA itself but contains a java module which is 
based on the similar Java code from the TIKA sources. The module is intended for extracting text and coordinates from 
PDF files with PDFBox. 
