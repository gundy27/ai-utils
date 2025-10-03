"""Example demonstrating chunk splitting for LLM token limits."""

import asyncio
import tempfile
from pathlib import Path

from gundy_ai.data_pipelines import (
    EnhancedDocumentProcessor,
    EnhancedTextChunker,
    ProcessorConfig,
    ChunkSplittingFilter,
    OutputManager,
    OutputFormat,
)


async def create_large_document():
    """Create a large document that will exceed token limits."""

    # Create a document with content that will result in oversized chunks
    large_content = """
# Clinical Reasoning in Small Animal Practice

## Introduction

Clinical reasoning is the cognitive process that enables practitioners to observe, collect, and analyze information to make informed decisions about patient care. In small animal practice, this process is particularly complex due to the inability of patients to verbally communicate their symptoms, making the veterinarian's observational and analytical skills paramount.

The foundation of clinical reasoning rests on several key principles: systematic observation, pattern recognition, hypothesis generation, and evidence-based decision making. These principles guide veterinarians through the diagnostic process, from initial presentation to treatment implementation and monitoring.

## Systematic Approach to Clinical Reasoning

### History Taking

A comprehensive history forms the cornerstone of clinical reasoning. This includes obtaining information about the animal's signalment (species, breed, age, sex, reproductive status), presenting complaint, duration and progression of symptoms, previous medical history, vaccination status, diet, environment, and any recent changes in routine or behavior.

The art of history taking in veterinary medicine requires skilled communication with pet owners, who may not always recognize the significance of certain observations or may inadvertently omit crucial details. Veterinarians must ask targeted questions while remaining open to unexpected information that might redirect their diagnostic thinking.

### Physical Examination

The physical examination provides objective data to complement the subjective information gathered during history taking. A systematic approach ensures thoroughness and consistency, reducing the likelihood of missing important findings.

The examination should follow a logical sequence: general observation of the animal's demeanor and posture, assessment of vital signs (temperature, pulse, respiration), and systematic evaluation of body systems. Each finding should be interpreted in the context of the patient's signalment and presenting complaint.

### Diagnostic Testing

Laboratory tests, imaging studies, and other diagnostic procedures serve to confirm or refute clinical hypotheses. The selection of appropriate tests requires careful consideration of their sensitivity, specificity, predictive values, and cost-effectiveness.

Common diagnostic modalities in small animal practice include complete blood count, serum chemistry panels, urinalysis, fecal examinations, radiography, ultrasonography, electrocardiography, and various specialized tests depending on the suspected condition.

## Pattern Recognition and Hypothesis Generation

Experienced clinicians develop pattern recognition skills that allow them to quickly identify common presentations and generate appropriate differential diagnoses. This cognitive shortcut, while efficient, must be balanced with systematic thinking to avoid premature closure and diagnostic errors.

The generation of differential diagnoses should be comprehensive initially, then systematically narrowed through additional history, physical examination findings, and diagnostic test results. The VINDICATE mnemonic (Vascular, Inflammatory/Infectious, Neoplastic, Degenerative, Idiopathic, Congenital, Autoimmune, Traumatic, Endocrine) provides a useful framework for ensuring comprehensive consideration of disease categories.

### Common Diagnostic Challenges

Small animal practitioners frequently encounter diagnostic challenges that require sophisticated clinical reasoning skills. These include:

1. **Multisystem diseases**: Conditions that affect multiple organ systems simultaneously can present with complex, seemingly unrelated symptoms that require careful integration of findings.

2. **Subclinical conditions**: Early-stage diseases may present with subtle signs that are easily overlooked without careful observation and systematic evaluation.

3. **Concurrent conditions**: Multiple diseases occurring simultaneously can mask or modify the typical presentation of individual conditions.

4. **Age-related considerations**: Geriatric animals may present with multiple concurrent conditions, while young animals may have congenital or developmental abnormalities.

## Evidence-Based Decision Making

Modern veterinary practice increasingly emphasizes evidence-based medicine, which integrates the best available research evidence with clinical expertise and patient/client values. This approach requires practitioners to critically evaluate scientific literature and apply research findings to individual cases.

The hierarchy of evidence places systematic reviews and meta-analyses at the top, followed by randomized controlled trials, cohort studies, case-control studies, case series, and expert opinion. Understanding this hierarchy helps practitioners weigh the strength of evidence supporting different diagnostic and treatment approaches.

### Critical Appraisal Skills

Veterinarians must develop skills in critically appraising research literature, including understanding study design, statistical analysis, and potential sources of bias. This enables them to make informed decisions about incorporating new research findings into their practice.

Key questions to consider when evaluating research include: Is the study population relevant to my patient? Are the methods sound? Are the results clinically significant as well as statistically significant? Are there potential conflicts of interest or sources of bias?

## Cognitive Biases and Diagnostic Errors

Understanding common cognitive biases can help practitioners recognize and mitigate potential sources of diagnostic error. Common biases in clinical reasoning include:

**Anchoring bias**: Over-reliance on the first piece of information encountered, leading to inadequate consideration of alternative diagnoses.

**Confirmation bias**: Seeking information that confirms initial impressions while ignoring contradictory evidence.

**Availability bias**: Overestimating the likelihood of conditions that come readily to mind, often due to recent experience or memorable cases.

**Premature closure**: Accepting a diagnosis before it has been fully verified, potentially missing alternative or additional diagnoses.

### Strategies for Reducing Diagnostic Errors

Several strategies can help reduce diagnostic errors:

1. **Systematic approach**: Following a consistent diagnostic process reduces the likelihood of missing important steps or considerations.

2. **Differential diagnosis lists**: Maintaining comprehensive differential diagnosis lists and systematically working through them helps ensure thorough consideration of possibilities.

3. **Seeking second opinions**: Consulting with colleagues or specialists can provide fresh perspectives and identify potential oversights.

4. **Continuous learning**: Staying current with veterinary literature and participating in continuing education helps maintain and expand diagnostic skills.

## Case-Based Learning

Case-based learning provides an effective method for developing and refining clinical reasoning skills. By working through real or simulated cases, practitioners can practice applying systematic approaches to diagnosis and treatment while learning from both successes and mistakes.

Effective case-based learning involves:

- Systematic presentation of case information
- Generation of differential diagnoses
- Selection and interpretation of diagnostic tests
- Development of treatment plans
- Monitoring and adjustment of therapy
- Reflection on the diagnostic process and outcomes

### Example Case Study

Consider a 7-year-old spayed female Golden Retriever presenting with a 3-day history of lethargy, decreased appetite, and vomiting. The owner reports that the dog has been drinking more water than usual and had an episode of diarrhea yesterday.

Initial assessment reveals a mildly dehydrated dog with a temperature of 102.8°F, heart rate of 120 bpm, and respiratory rate of 28 breaths per minute. Physical examination findings include mild abdominal discomfort on palpation and slightly pale mucous membranes.

This presentation could suggest several differential diagnoses, including gastroenteritis, pancreatitis, kidney disease, liver disease, or systemic infection. The systematic approach would involve obtaining additional history, performing targeted diagnostic tests, and interpreting results in the context of the clinical presentation.

## Technology and Clinical Reasoning

Modern technology provides numerous tools to support clinical reasoning, including electronic medical records, diagnostic imaging, laboratory analyzers, and decision support systems. While these tools can enhance diagnostic accuracy and efficiency, they should complement rather than replace fundamental clinical reasoning skills.

Artificial intelligence and machine learning applications are increasingly being developed for veterinary medicine, offering potential benefits in pattern recognition, diagnostic assistance, and treatment recommendations. However, the integration of these technologies requires careful consideration of their limitations and the continued importance of clinical judgment.

## Conclusion

Clinical reasoning in small animal practice is a complex cognitive process that combines scientific knowledge, observational skills, and analytical thinking. Developing expertise in clinical reasoning requires continuous learning, practice, and reflection on diagnostic processes and outcomes.

The systematic approach to clinical reasoning, combined with awareness of cognitive biases and commitment to evidence-based practice, provides the foundation for accurate diagnosis and effective treatment. As veterinary medicine continues to evolve with new technologies and research findings, the fundamental principles of clinical reasoning remain essential for providing optimal patient care.

Practitioners who invest in developing strong clinical reasoning skills will be better equipped to handle the diagnostic challenges inherent in small animal practice and provide the highest quality care for their patients. The integration of systematic thinking, pattern recognition, and evidence-based decision making creates a robust framework for clinical excellence.

Through continued education, case-based learning, and reflective practice, veterinarians can refine their clinical reasoning abilities throughout their careers, ultimately benefiting both their patients and the advancement of veterinary medicine as a whole.
    """.strip()

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(large_content)
        return f.name


async def demonstrate_chunk_splitting():
    """Demonstrate chunk splitting functionality."""

    print("✂️  Chunk Splitting Demo")
    print("=" * 50)
    print()

    # Create a large document
    large_doc_path = await create_large_document()

    try:
        # Step 1: Process document with regular chunking (will create oversized chunks)
        print("📄 Step 1: Processing with regular chunking...")

        doc_processor = EnhancedDocumentProcessor(
            config=ProcessorConfig(name="regular_processing")
        )

        regular_chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="regular_chunker"),
            strategy="structure_aware",
            chunk_size=4000,  # Large chunks that might exceed token limits
            overlap=200,
        )

        # Process document
        doc_result = await doc_processor.process(large_doc_path)

        if not doc_result.success:
            print(f"❌ Document processing failed: {doc_result.error}")
            return

        document = doc_result.data
        print(f"✅ Document processed: {len(document.full_text):,} characters")

        # Chunk with regular strategy
        chunk_result = await regular_chunker.process(document)

        if not chunk_result.success:
            print(f"❌ Chunking failed: {chunk_result.error}")
            return

        regular_doc = chunk_result.data
        print(f"✅ Regular chunking: {len(regular_doc.chunks)} chunks created")

        # Analyze chunk sizes
        oversized_chunks = []
        for i, chunk in enumerate(regular_doc.chunks):
            # Rough token estimation (1 token ≈ 4 characters)
            estimated_tokens = len(chunk.content) // 4
            print(
                f"   Chunk {i+1}: {len(chunk.content):,} chars (~{estimated_tokens:,} tokens)"
            )

            if estimated_tokens > 8192:  # OpenAI's limit
                oversized_chunks.append((i, chunk, estimated_tokens))

        if oversized_chunks:
            print(
                f"⚠️  Found {len(oversized_chunks)} oversized chunks exceeding 8,192 tokens!"
            )
            for i, chunk, tokens in oversized_chunks:
                print(
                    f"   Chunk {i+1}: ~{tokens:,} tokens (exceeds limit by {tokens-8192:,})"
                )
        else:
            print("✅ All chunks are within token limits")

        print()

        # Step 2: Apply chunk splitting filter
        print("🔧 Step 2: Applying chunk splitting filter...")

        chunk_filter = ChunkSplittingFilter(
            max_tokens=8192,  # OpenAI's limit
            target_tokens=4000,  # Target size for split chunks
            overlap_tokens=200,  # Overlap between split chunks
        )

        filtered_doc = await chunk_filter.filter_document(regular_doc)

        print("✅ Chunk splitting applied")
        print(f"   Original chunks: {len(regular_doc.chunks)}")
        print(f"   Final chunks: {len(filtered_doc.chunks)}")

        # Analyze filtered chunks
        max_tokens = 0
        total_tokens = 0
        split_chunks = 0

        for i, chunk in enumerate(filtered_doc.chunks):
            estimated_tokens = len(chunk.content) // 4
            total_tokens += estimated_tokens
            max_tokens = max(max_tokens, estimated_tokens)

            if "split_from" in chunk.metadata:
                split_chunks += 1

            print(
                f"   Chunk {i+1}: {len(chunk.content):,} chars (~{estimated_tokens:,} tokens)"
            )

            # Show split metadata if available
            if "split_from" in chunk.metadata:
                split_info = chunk.metadata
                print(
                    f"      ↳ Split from chunk {split_info['split_from']} "
                    f"(part {split_info['split_part']}/{split_info['split_total']})"
                )

        print("📊 Final statistics:")
        print(f"   Total chunks: {len(filtered_doc.chunks)}")
        print(f"   Split chunks: {split_chunks}")
        print(f"   Max tokens in any chunk: ~{max_tokens:,}")
        print(
            f"   Average tokens per chunk: ~{total_tokens // len(filtered_doc.chunks):,}"
        )
        print()

        # Step 3: Demonstrate token-aware chunking from the start
        print("🎯 Step 3: Token-aware chunking from the start...")

        token_aware_chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="token_aware_chunker"),
            strategy="token_aware",
            chunk_size=4000,  # Target tokens (not characters)
            overlap=200,  # Overlap in tokens
            max_tokens=8192,  # Hard limit
            encoding_name="cl100k_base",  # GPT-4 encoding
        )

        # Process with token-aware chunking
        token_result = await token_aware_chunker.process(document)

        if token_result.success:
            token_doc = token_result.data
            print(f"✅ Token-aware chunking: {len(token_doc.chunks)} chunks created")

            for i, chunk in enumerate(token_doc.chunks):
                actual_tokens = (
                    chunk.token_count
                    if hasattr(chunk, "token_count")
                    else len(chunk.content) // 4
                )
                print(
                    f"   Chunk {i+1}: {len(chunk.content):,} chars (~{actual_tokens:,} tokens)"
                )

            # Show metadata
            metadata = token_result.metadata
            print("📊 Token-aware statistics:")
            print(
                f"   Average tokens per chunk: {metadata.get('avg_tokens_per_chunk', 0):.0f}"
            )
            print(
                f"   Max tokens in chunk: {metadata.get('max_tokens_in_chunk', 0):.0f}"
            )
            print(f"   Encoding used: {metadata.get('encoding', 'unknown')}")
        else:
            print(f"❌ Token-aware chunking failed: {token_result.error}")

        print()

        # Step 4: Export results for comparison
        print("💾 Step 4: Exporting results...")

        output_manager = OutputManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Export regular chunks
            regular_result = await output_manager.write_document(
                regular_doc, Path(temp_dir) / "regular_chunks.json", OutputFormat.JSON
            )

            # Export filtered chunks
            filtered_result = await output_manager.write_document(
                filtered_doc, Path(temp_dir) / "filtered_chunks.json", OutputFormat.JSON
            )

            # Export token-aware chunks
            if token_result.success:
                token_export_result = await output_manager.write_document(
                    token_doc,
                    Path(temp_dir) / "token_aware_chunks.json",
                    OutputFormat.JSON,
                )

                print("✅ Exported results:")
                print(f"   Regular chunks: {regular_result.file_size / 1024:.1f} KB")
                print(f"   Filtered chunks: {filtered_result.file_size / 1024:.1f} KB")
                print(
                    f"   Token-aware chunks: {token_export_result.file_size / 1024:.1f} KB"
                )

        print()
        print("🎯 Key Benefits of Chunk Splitting:")
        print("   ✅ Preserves all content (no data loss)")
        print("   ✅ Ensures LLM compatibility (respects token limits)")
        print("   ✅ Maintains context with overlapping chunks")
        print("   ✅ Preserves document structure when possible")
        print("   ✅ Provides detailed metadata about splitting")
        print("   ✅ Works with any existing chunking strategy")

        print()
        print("🔧 Configuration Options:")
        print("   • max_tokens: Hard limit (e.g., 8192 for OpenAI)")
        print("   • target_tokens: Preferred chunk size")
        print("   • overlap_tokens: Overlap between split chunks")
        print("   • encoding_name: Tokenizer to use (cl100k_base, p50k_base, etc.)")
        print("   • preserve_sentences: Try to split at sentence boundaries")
        print("   • preserve_paragraphs: Try to split at paragraph boundaries")

    finally:
        # Cleanup
        Path(large_doc_path).unlink(missing_ok=True)


async def main():
    """Main demo function."""
    print("🚀 Chunk Splitting for LLM Token Limits")
    print("=" * 60)
    print()
    print("This demo shows how to handle documents that create chunks")
    print("exceeding LLM token limits (like OpenAI's 8,192 token limit).")
    print()

    await demonstrate_chunk_splitting()

    print()
    print("🎉 Demo Complete!")
    print()
    print("💡 Usage in Your Pipeline:")
    print()
    print("# Option 1: Use ChunkSplittingFilter on existing chunks")
    print("from gundy_ai.data_pipelines import ChunkSplittingFilter")
    print()
    print("filter = ChunkSplittingFilter(max_tokens=8192)")
    print("filtered_doc = await filter.filter_document(document)")
    print()
    print("# Option 2: Use TokenAwareChunker from the start")
    print("from gundy_ai.data_pipelines import EnhancedTextChunker")
    print()
    print("chunker = EnhancedTextChunker(")
    print("    config=ProcessorConfig(name='token_aware'),")
    print("    strategy='token_aware',")
    print("    chunk_size=4000,  # Target tokens")
    print("    max_tokens=8192   # Hard limit")
    print(")")


if __name__ == "__main__":
    asyncio.run(main())
