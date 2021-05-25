package com.lexpredict.textextraction;

import com.lexpredict.textextraction.dto.PDFTOCRef;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.common.PDNameTreeNode;
import org.apache.pdfbox.pdmodel.interactive.action.PDAction;
import org.apache.pdfbox.pdmodel.interactive.action.PDActionGoTo;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.destination.PDDestination;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.destination.PDNamedDestination;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.destination.PDPageDestination;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.destination.PDPageXYZDestination;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDDocumentOutline;
import org.apache.pdfbox.pdmodel.interactive.documentnavigation.outline.PDOutlineItem;
import org.msgpack.jackson.dataformat.Tuple;

import java.io.IOException;
import java.util.*;

/*
* This static class reads Table Of Contents and returns a list of PDFTOCRef records
* */
public class GetTOCFromPDF {
    private static void readTOCRawItems(
            Map<String, Tuple<Integer, PDAction>> map,
            PDOutlineItem root,
            int level) {
        // populate a flat list of table of contents raw data that is
        // actually a tree
        map.put(root.getTitle(), new Tuple<>(level, root.getAction()));
        PDOutlineItem child = root.getFirstChild();
        while (child != null) {
            readTOCRawItems(map, child, level + 1);
            child = child.getNextSibling();
        }
    }

    public static List<PDFTOCRef> getTableOfContents(PDDocument document) throws IOException {
        List<PDFTOCRef> tocItems = new ArrayList<>();
        // read pages into a flat list to find the page index later
        List<PDPage> pages = new ArrayList<>();
        for (PDPage page: document.getPages()) {
            pages.add(page);
        }

        PDDocumentOutline bookmarks = document.getDocumentCatalog().getDocumentOutline();
        if (bookmarks == null)
            return tocItems;

        Map<String, Tuple<Integer, PDAction>> map = new HashMap<>();
        for (PDOutlineItem item: bookmarks.children()) {
            readTOCRawItems(map, item, 1);
        }

        // read all document references - we expect PDPageXYZDestination
        // that just point to the certain location on the document "canvas"
        Map<String, PDPageDestination> dests = getAllNamedDestinations(document);

        for (String key : map.keySet()) {
            Tuple<Integer, PDAction> levelAction = map.get(key);
            if (!(levelAction.second() instanceof PDActionGoTo))
                continue;
            PDActionGoTo goToAction = (PDActionGoTo) levelAction.second();
            PDDestination dest = goToAction.getDestination();

            if (!(dest instanceof PDNamedDestination))
                continue;
            PDNamedDestination namedDest = (PDNamedDestination) dest;
            String destName = namedDest.getNamedDestination();
            PDPageDestination pd = dests.get(destName);
            PDPage refPage = pd.getPage();
            int pageIndex = pages.indexOf(refPage);
            PDFTOCRef tRef = new PDFTOCRef(key, levelAction.first(), 0, 0, pageIndex);
            if (pd instanceof PDPageXYZDestination) {
                PDPageXYZDestination pdXY = (PDPageXYZDestination) pd;
                tRef.left = pdXY.getLeft();
                tRef.top = pdXY.getTop();
            }
            tocItems.add(tRef);
        }
        tocItems.sort(Comparator.comparingInt(s -> s.page));
        return tocItems;
    }

    private static Map<String, PDPageDestination> getAllNamedDestinations(PDDocument document) {
        // returns { name: page_destination } map from the document's tree-like catalog
        Map<String, PDPageDestination> namedDestinations = new HashMap<>(10);
        PDDocumentCatalog documentCatalog = document.getDocumentCatalog();
        PDDocumentNameDictionary names = documentCatalog.getNames();

        if (names == null)
            return namedDestinations;

        PDDestinationNameTreeNode dests = names.getDests();

        try {
            if (dests.getNames() != null)
                namedDestinations.putAll(dests.getNames());
        } catch (Exception e) {
            e.printStackTrace();
        }

        List<PDNameTreeNode<PDPageDestination>> kids = dests.getKids();
        traverseKids(kids, namedDestinations);
        return namedDestinations;
    }

    private static void traverseKids(List<PDNameTreeNode<PDPageDestination>> kids,
                                     Map<String, PDPageDestination> namedDestinations) {
        if (kids == null)
            return;

        try {
            for(PDNameTreeNode<PDPageDestination> kid : kids){
                if(kid.getNames() != null){
                    try {
                        namedDestinations.putAll(kid.getNames());
                    } catch (Exception e) {
                        System.out.println("INFO: Duplicate named destinations in document.");
                        e.printStackTrace();
                    }
                }
                if (kid.getKids() != null)
                    traverseKids(kid.getKids(), namedDestinations);
            }
        } catch (Exception e){
            e.printStackTrace();
        }
    }
}
