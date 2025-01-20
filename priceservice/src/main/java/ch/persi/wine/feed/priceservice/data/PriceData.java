package ch.persi.wine.feed.priceservice.data;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import lombok.Data;

@Entity
@Data // Generiert Getter, Setter, toString, equals und hashCode
public class PriceData {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String column1;
    private String column2;
    // Weitere Spalten hinzufügen
}
