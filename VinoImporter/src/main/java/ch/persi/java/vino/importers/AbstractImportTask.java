package ch.persi.java.vino.importers;

import ch.persi.java.vino.domain.Origin;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.util.InputParser;
import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;

import java.io.File;
import java.io.FileWriter;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
public abstract class AbstractImportTask implements ImportTask {

    protected InputParser parser = null;
    protected FileWriter anOutputWriter = null;
    protected FileWriter aSkippedRowsWriter = null;

    @Setter
    @Getter
    private LocalDate auctionDate = null;
    @Setter
    @Getter
    private String eventIdentifier = null;

    @Autowired
    public void setInputParser(InputParser theInputParser) {
        parser = theInputParser;
    }

    public static String getOrigin(final String theLine) {
        // is it the origin line ?
        for (Origin anOrigin : Origin.values()) {
            Pattern aCompiledOriginPattern = Pattern.compile("^(" + anOrigin.getOriginIdentifier() + ")\\,.*");
            Matcher matcher = aCompiledOriginPattern.matcher(theLine);
            if (matcher.matches()) {
                return matcher.group(1);
            }
        }
        return null;
    }

    protected void importFile(final List<String> someLines, final Provider theProvider) throws Exception {
        if (getAuctionDate() == null) {
            throw new IllegalStateException("Cannot get an auction date, this is a serious problem !");
        }

        try {
            anOutputWriter = new FileWriter("output_" + theProvider.getProviderCode() + "_" + getAuctionDate().format(DateTimeFormatter.ofPattern("ddMMyyyy")) + ".log");
            aSkippedRowsWriter = new FileWriter("skippedRowsFrom_" + theProvider.getProviderCode() + "_" + getAuctionDate().format(DateTimeFormatter.ofPattern("ddMMyyyy")) + ".log");
            saveWineOfferings(someLines);
        } catch (Exception theCause) {
            log.error(theCause.getMessage(), theCause);
        } finally {
            if (anOutputWriter != null) {
                anOutputWriter.flush();
                anOutputWriter.close();
            }

            if (aSkippedRowsWriter != null) {
                aSkippedRowsWriter.flush();
                aSkippedRowsWriter.close();
            }

        }
    }

    public abstract String getImportDirectory();

    protected File checkFiles() {

        // checking for to be imported files at fileSystem, apply some validation
        String anImportDirectoryPath = getImportDirectory();
        File anImportFile = new File(anImportDirectoryPath);
        if (anImportFile.list() == null || Objects.requireNonNull(anImportFile.list()).length < 1) {
            log.error("The import directory {} does not exist or does not contain anything at all !", anImportFile);
            return null;
        }
        return anImportFile;
    }

}
