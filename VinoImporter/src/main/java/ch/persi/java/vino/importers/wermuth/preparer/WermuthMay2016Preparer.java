package ch.persi.java.vino.importers.wermuth.preparer;

import java.io.FileNotFoundException;

public class WermuthMay2016Preparer extends BaseWermuthPreparer {

    public static void main(String[] args) throws FileNotFoundException {
        new WermuthMay2016Preparer().prepare();
    }

    @Override
    protected String getInputFilePath() {
        return "import/Wermuth/WZ-257_Resultate_15052016";
    }
}
