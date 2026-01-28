package ch.persi.java.vino.importers.wermuth.preparer;

import java.io.FileNotFoundException;

public class WermuthSeptember2016Preparer extends BaseWermuthPreparer {

    public static void main(String[] args) throws FileNotFoundException {
        new WermuthSeptember2016Preparer().prepare();
    }

    @Override
    protected String getInputFilePath() {
        return "import/Wermuth/WZ-259_Resultate_18092016";
    }
}
