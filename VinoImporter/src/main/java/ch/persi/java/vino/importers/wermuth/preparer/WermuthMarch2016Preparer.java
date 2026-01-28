package ch.persi.java.vino.importers.wermuth.preparer;

import java.io.FileNotFoundException;

public class WermuthMarch2016Preparer extends BaseWermuthPreparer {

    public static void main(String[] args) throws FileNotFoundException {
        new WermuthMarch2016Preparer().prepare();
    }

    @Override
    protected String getInputFilePath() {
        return "import/Wermuth/WZ-256_Resultate_13032016";
    }
}
